import os, time, json
from typing import Set, List
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from langdetect import detect, DetectorFactory
from simhash import Simhash

try:
    from .config import (
        ALLOWED_DOMAINS, START_URLS, CRAWL_MAX_PAGES, CRAWL_RATE_SECONDS, USER_AGENT,
        OUTPUT_JSONL
    )
    from .chunker import split_into_chunks
except ImportError:
    from config import (
        ALLOWED_DOMAINS, START_URLS, CRAWL_MAX_PAGES, CRAWL_RATE_SECONDS, USER_AGENT,
        OUTPUT_JSONL
    )
    from chunker import split_into_chunks

DetectorFactory.seed = 0

def setup_driver():
    """Setup Chrome driver with appropriate options"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in background
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument(f"--user-agent={USER_AGENT}")
    chrome_options.add_argument("--window-size=1920,1080")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        return driver
    except WebDriverException as e:
        print(f"[crawler] Chrome driver error: {e}")
        print("[crawler] Please install Chrome and ChromeDriver")
        return None

def extract_text_selenium(driver, url: str) -> tuple[str, str]:
    """Extract text content using Selenium"""
    try:
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Wait a bit more for JavaScript to render content
        time.sleep(3)
        
        # Get title
        title = driver.title if driver.title else ""
        
        # Try to find main content areas
        content_selectors = [
            "main", "[role='main']", ".main", "#main", ".content", "#content",
            ".container", ".wrapper", "article", ".article", ".post", "body"
        ]
        
        text_content = ""
        for selector in content_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    for element in elements:
                        text = element.text.strip()
                        if text and len(text) > len(text_content):
                            text_content = text
            except Exception:
                continue
        
        # If no specific content found, get all text
        if not text_content or len(text_content) < 100:
            text_content = driver.find_element(By.TAG_NAME, "body").text.strip()
        
        return title, text_content
        
    except TimeoutException:
        print(f"[crawler] Timeout waiting for {url}")
        return "", ""
    except Exception as e:
        print(f"[crawler] Error extracting text from {url}: {e}")
        return "", ""

def discover_links_selenium(driver, base_url: str) -> Set[str]:
    """Discover links using Selenium"""
    links = set()
    try:
        # Find all anchor tags
        anchor_elements = driver.find_elements(By.TAG_NAME, "a")
        for anchor in anchor_elements:
            try:
                href = anchor.get_attribute("href")
                if href and "htu.edu.jo" in href:
                    links.add(href)
            except Exception:
                continue
    except Exception as e:
        print(f"[crawler] Error discovering links: {e}")
    
    return links

def get_manual_urls() -> Set[str]:
    """Get manually specified URLs for important pages"""
    base_domain = "https://www.htu.edu.jo"
    manual_urls = {
        f"{base_domain}/",
        f"{base_domain}/ar/",
        f"{base_domain}/about/",
        f"{base_domain}/ar/about/",
        f"{base_domain}/academics/",
        f"{base_domain}/ar/academics/",
        f"{base_domain}/admissions/",
        f"{base_domain}/ar/admissions/",
        f"{base_domain}/research/",
        f"{base_domain}/ar/research/",
        f"{base_domain}/contact/",
        f"{base_domain}/ar/contact/",
        f"{base_domain}/news/",
        f"{base_domain}/ar/news/",
        f"{base_domain}/faculty/",
        f"{base_domain}/ar/faculty/",
        f"{base_domain}/programs/",
        f"{base_domain}/ar/programs/",
    }
    return manual_urls

def crawl_selenium():
    """Crawl using Selenium to handle JavaScript-rendered content"""
    print("[crawler] Starting Selenium-based crawler...")
    
    driver = setup_driver()
    if not driver:
        print("[crawler] Failed to setup Chrome driver")
        return
    
    try:
        # Start with manual URLs
        queue: Set[str] = set(START_URLS)
        queue.update(get_manual_urls())
        
        print(f"[crawler] Total URLs in queue: {len(queue)}")
        
        seen: Set[str] = set()
        out_rows: List[dict] = []
        content_hashes: Set[int] = set()
        pages = 0
        
        while queue and pages < CRAWL_MAX_PAGES:
            url = queue.pop()
            if url in seen:
                continue
            seen.add(url)
            
            print(f"[crawler] Processing {url} ({pages + 1}/{CRAWL_MAX_PAGES})")
            
            try:
                driver.get(url)
                time.sleep(CRAWL_RATE_SECONDS)
                
                # Extract text content
                title, text = extract_text_selenium(driver, url)
                
                if not text or len(text) < 100:
                    print(f"[crawler] Insufficient text for {url}: {len(text)} chars")
                    continue
                
                print(f"[crawler] Extracted {len(text)} chars from {url}")
                
                # Language detection
                lang = "ar" if "/ar/" in url else "en"
                try:
                    det = detect(text[:2000])
                    if det.startswith("ar"):
                        lang = "ar"
                    elif det.startswith("en"):
                        lang = "en"
                except Exception:
                    pass
                
                # Near-duplicate detection
                sh = Simhash(text).value
                if any(bin(prev ^ sh).count("1") <= 3 for prev in content_hashes):
                    print(f"[crawler] Duplicate content detected for {url}")
                    continue
                content_hashes.add(sh)
                
                # Chunk and save
                chunks = split_into_chunks(text, chunk_size=1400, overlap=150)
                for i, ch in enumerate(chunks):
                    out_rows.append({
                        "id": f"{url}#chunk={i}",
                        "url": url,
                        "title": title,
                        "content": ch,
                        "lang": lang,
                        "last_modified": "",
                        "content_type": "html",
                    })
                
                pages += 1
                
                # Discover more links
                try:
                    new_links = discover_links_selenium(driver, url)
                    for u in new_links:
                        if u not in seen and u not in queue and len(queue) < 1000:
                            queue.add(u)
                    print(f"[crawler] Discovered {len(new_links)} new links from {url}")
                except Exception as e:
                    print(f"[crawler] Link discovery error for {url}: {e}")
                
            except Exception as e:
                print(f"[crawler] Error processing {url}: {e}")
                continue
        
        # Save results
        os.makedirs(os.path.join(os.path.dirname(__file__), "..", "data"), exist_ok=True)
        out_path = os.path.join(os.path.dirname(__file__), "..", "data", "university_corpus.jsonl")
        
        with open(out_path, "w", encoding="utf-8") as f:
            for row in out_rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        
        print(f"[crawler] Wrote {len(out_rows)} chunks from {pages} pages to {out_path}")
        print(f"[crawler] Total URLs discovered: {len(seen)}")
        print(f"[crawler] URLs remaining in queue: {len(queue)}")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    crawl_selenium()

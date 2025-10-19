import os, time, httpx
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from langdetect import detect, DetectorFactory
from simhash import Simhash
import json
from typing import Set, List
import re

try:
    from .config import (
        ALLOWED_DOMAINS, START_URLS, CRAWL_MAX_PAGES, CRAWL_RATE_SECONDS, USER_AGENT,
        OUTPUT_JSONL
    )
    from .extract import extract_text_from_pdf, extract_text_from_html
    from .chunker import split_into_chunks
except ImportError:
    from config import (
        ALLOWED_DOMAINS, START_URLS, CRAWL_MAX_PAGES, CRAWL_RATE_SECONDS, USER_AGENT,
        OUTPUT_JSONL
    )
    from extract import extract_text_from_pdf, extract_text_from_html
    from chunker import split_into_chunks

DetectorFactory.seed = 0
session = httpx.Client(timeout=30.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True)

def allowed(url: str) -> bool:
    netloc = urlparse(url).netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return any(netloc == d or netloc.endswith("." + d) for d in ALLOWED_DOMAINS)

def canonicalize(u: str) -> str:
    u = u.split("#")[0]
    if u.endswith("/index.html"):
        return u[:-10]
    return u

def get_static_content_urls() -> Set[str]:
    """Get URLs that might contain static content"""
    base_domain = "https://www.htu.edu.jo"
    
    # Common static content paths
    static_paths = [
        # Main pages
        "/", "/ar/",
        
        # About and information
        "/about/", "/ar/about/", "/about-us/", "/ar/about-us/",
        "/mission/", "/ar/mission/", "/vision/", "/ar/vision/",
        "/history/", "/ar/history/", "/leadership/", "/ar/leadership/",
        
        # Academic information
        "/academics/", "/ar/academics/", "/academic/", "/ar/academic/",
        "/programs/", "/ar/programs/", "/courses/", "/ar/courses/",
        "/departments/", "/ar/departments/", "/faculties/", "/ar/faculties/",
        "/schools/", "/ar/schools/", "/colleges/", "/ar/colleges/",
        
        # Student information
        "/admissions/", "/ar/admissions/", "/students/", "/ar/students/",
        "/student-life/", "/ar/student-life/", "/campus/", "/ar/campus/",
        "/library/", "/ar/library/", "/services/", "/ar/services/",
        
        # Research and faculty
        "/research/", "/ar/research/", "/faculty/", "/ar/faculty/",
        "/staff/", "/ar/staff/", "/publications/", "/ar/publications/",
        
        # News and events
        "/news/", "/ar/news/", "/events/", "/ar/events/",
        "/announcements/", "/ar/announcements/", "/updates/", "/ar/updates/",
        
        # Contact and location
        "/contact/", "/ar/contact/", "/location/", "/ar/location/",
        "/directions/", "/ar/directions/", "/map/", "/ar/map/",
        
        # Resources
        "/resources/", "/ar/resources/", "/downloads/", "/ar/downloads/",
        "/forms/", "/ar/forms/", "/documents/", "/ar/documents/",
        
        # Specific academic areas
        "/engineering/", "/ar/engineering/", "/technology/", "/ar/technology/",
        "/business/", "/ar/business/", "/arts/", "/ar/arts/",
        "/sciences/", "/ar/sciences/", "/medicine/", "/ar/medicine/",
        
        # Administrative
        "/administration/", "/ar/administration/", "/governance/", "/ar/governance/",
        "/policies/", "/ar/policies/", "/regulations/", "/ar/regulations/",
    ]
    
    urls = set()
    for path in static_paths:
        urls.add(f"{base_domain}{path}")
    
    return urls

def extract_text_robust(html_content: bytes, url: str) -> tuple[str, str]:
    """Robust text extraction that tries multiple strategies"""
    html_str = html_content.decode("utf-8", errors="replace")
    
    # Method 1: Try trafilatura (original method)
    try:
        title, text = extract_text_from_html(html_content)
        if text and len(text.strip()) > 100:
            return title, text
    except Exception:
        pass
    
    # Method 2: Look for specific content patterns
    try:
        soup = BeautifulSoup(html_str, "lxml")
        
        # Get title
        title = ""
        if soup.title and soup.title.text:
            title = soup.title.text.strip()
        
        # Look for content in common patterns
        content_patterns = [
            # Meta descriptions
            'meta[name="description"]',
            'meta[property="og:description"]',
            
            # Common content containers
            'main', '[role="main"]', '.main', '#main', '.content', '#content',
            '.container', '.wrapper', '.page-content', '.entry-content',
            'article', '.article', '.post', '.post-content',
            
            # Specific content areas
            '.hero-content', '.banner-content', '.intro-text', '.overview',
            '.description', '.summary', '.details', '.info',
            
            # Text content
            'p', '.text', '.body-text', '.content-text'
        ]
        
        extracted_texts = []
        
        # Try meta descriptions first
        for pattern in content_patterns[:2]:
            elements = soup.select(pattern)
            for element in elements:
                content = element.get('content', '') or element.get_text(strip=True)
                if content and len(content) > 50:
                    extracted_texts.append(content)
        
        # Try main content areas
        for pattern in content_patterns[2:]:
            elements = soup.select(pattern)
            for element in elements:
                text = element.get_text(separator=" ", strip=True)
                if text and len(text) > 100:
                    extracted_texts.append(text)
        
        # Combine all extracted text
        if extracted_texts:
            combined_text = " ".join(extracted_texts)
            combined_text = re.sub(r'\s+', ' ', combined_text).strip()
            if len(combined_text) > 100:
                return title, combined_text
        
    except Exception:
        pass
    
    # Method 3: Extract all text and clean it
    try:
        soup = BeautifulSoup(html_str, "lxml")
        
        # Remove unwanted elements
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        
        # Get all text
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r'\s+', ' ', text).strip()
        
        if text and len(text) > 100:
            return title, text
            
    except Exception:
        pass
    
    return "", ""

def crawl_static_content():
    """Crawl focusing on static content and common patterns"""
    print("[crawler] Starting static content crawler...")
    
    # Get URLs to crawl
    queue: Set[str] = set(START_URLS)
    queue.update(get_static_content_urls())
    
    print(f"[crawler] Total URLs in queue: {len(queue)}")
    
    seen: Set[str] = set()
    out_rows: List[dict] = []
    content_hashes: Set[int] = set()
    pages = 0
    
    while queue and pages < CRAWL_MAX_PAGES:
        url = queue.pop()
        if not allowed(url):
            continue
        url = canonicalize(url)
        if url in seen:
            continue
        seen.add(url)
        
        print(f"[crawler] Processing {url} ({pages + 1}/{CRAWL_MAX_PAGES})")
        
        try:
            time.sleep(CRAWL_RATE_SECONDS)
            resp = session.get(url)
        except Exception as e:
            print(f"[crawler] Error fetching {url}: {e}")
            continue
            
        if resp.status_code != 200 or not resp.content:
            print(f"[crawler] Bad response for {url}: {resp.status_code}")
            continue
        
        ctype = resp.headers.get("Content-Type", "").lower()
        last_mod = resp.headers.get("Last-Modified", "")
        title, text, kind = "", "", "other"
        
        if "pdf" in ctype or url.lower().endswith(".pdf"):
            kind = "pdf"
            try:
                text = extract_text_from_pdf(resp.content)
            except Exception as e:
                print(f"[crawler] PDF extraction error for {url}: {e}")
                text = ""
        elif "html" in ctype or url.lower().endswith((".html", ".htm", "/")):
            kind = "html"
            try:
                title, text = extract_text_robust(resp.content, url)
            except Exception as e:
                print(f"[crawler] HTML extraction error for {url}: {e}")
                text = ""
        else:
            continue
        
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
                "last_modified": last_mod,
                "content_type": kind,
            })
        
        pages += 1
        
        # Try to discover more links
        if kind == "html":
            try:
                soup = BeautifulSoup(resp.text, "lxml")
                links = soup.find_all("a", href=True)
                new_links = set()
                
                for link in links:
                    href = link.get("href", "")
                    if href:
                        full_url = urljoin(url, href)
                        if allowed(full_url) and full_url not in seen and full_url not in queue:
                            new_links.add(full_url)
                
                queue.update(new_links)
                print(f"[crawler] Discovered {len(new_links)} new links from {url}")
                
            except Exception as e:
                print(f"[crawler] Link discovery error for {url}: {e}")
    
    # Save results
    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "data"), exist_ok=True)
    out_path = os.path.join(os.path.dirname(__file__), "..", "data", "university_corpus.jsonl")
    
    with open(out_path, "w", encoding="utf-8") as f:
        for row in out_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    
    print(f"[crawler] Wrote {len(out_rows)} chunks from {pages} pages to {out_path}")
    print(f"[crawler] Total URLs discovered: {len(seen)}")
    print(f"[crawler] URLs remaining in queue: {len(queue)}")

if __name__ == "__main__":
    crawl_static_content()

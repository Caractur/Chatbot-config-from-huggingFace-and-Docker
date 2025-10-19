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

def extract_text_enhanced(html_content: bytes, url: str) -> tuple[str, str]:
    """Enhanced text extraction that tries multiple methods"""
    html_str = html_content.decode("utf-8", errors="replace")
    
    # Method 1: Try trafilatura (original method)
    try:
        title, text = extract_text_from_html(html_content)
        if text and len(text.strip()) > 100:
            return title, text
    except Exception:
        pass
    
    # Method 2: Basic BeautifulSoup extraction
    try:
        soup = BeautifulSoup(html_str, "lxml")
        
        # Get title
        title = ""
        if soup.title and soup.title.text:
            title = soup.title.text.strip()
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "header", "footer"]):
            script.decompose()
        
        # Extract text from remaining elements
        text_elements = []
        
        # Look for main content areas
        main_selectors = [
            "main", "[role='main']", ".main", "#main", ".content", "#content",
            ".container", ".wrapper", "article", ".article", ".post"
        ]
        
        for selector in main_selectors:
            elements = soup.select(selector)
            if elements:
                for element in elements:
                    text_elements.append(element.get_text(separator=" ", strip=True))
        
        # If no main content found, get all text
        if not text_elements:
            text_elements.append(soup.get_text(separator=" ", strip=True))
        
        text = " ".join(text_elements)
        
        # Clean up text
        text = re.sub(r'\s+', ' ', text).strip()
        
        if text and len(text) > 100:
            return title, text
            
    except Exception:
        pass
    
    # Method 3: Fallback to raw text extraction
    try:
        soup = BeautifulSoup(html_str, "lxml")
        title = soup.title.text.strip() if soup.title else ""
        
        # Remove all script, style, and meta tags
        for tag in soup(["script", "style", "meta", "link", "head"]):
            tag.decompose()
        
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r'\s+', ' ', text).strip()
        
        if text and len(text) > 100:
            return title, text
    except Exception:
        pass
    
    return "", ""

def discover_links_enhanced(html: str, base_url: str) -> Set[str]:
    """Enhanced link discovery that looks for various types of links"""
    soup = BeautifulSoup(html, "lxml")
    links = set()
    
    # Find all anchor tags
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if href:
            u = urljoin(base_url, href)
            if allowed(u):
                links.add(canonicalize(u))
    
    # Also look for links in JavaScript (common in SPAs)
    script_tags = soup.find_all("script")
    for script in script_tags:
        if script.string:
            # Look for URLs in JavaScript
            url_pattern = r'["\'](https?://[^"\']+)["\']'
            matches = re.findall(url_pattern, script.string)
            for match in matches:
                if allowed(match):
                    links.add(canonicalize(match))
    
    return links

def get_manual_urls() -> Set[str]:
    """Get manually specified URLs for important pages"""
    base_domain = "https://www.htu.edu.jo"
    manual_urls = {
        f"{base_domain}/",
        f"{base_domain}/ar/",
        f"{base_domain}/about",
        f"{base_domain}/ar/about",
        f"{base_domain}/academics",
        f"{base_domain}/ar/academics",
        f"{base_domain}/admissions",
        f"{base_domain}/ar/admissions",
        f"{base_domain}/research",
        f"{base_domain}/ar/research",
        f"{base_domain}/contact",
        f"{base_domain}/ar/contact",
        f"{base_domain}/news",
        f"{base_domain}/ar/news",
        f"{base_domain}/faculty",
        f"{base_domain}/ar/faculty",
        f"{base_domain}/programs",
        f"{base_domain}/ar/programs",
    }
    return manual_urls

def crawl_enhanced():
    """Enhanced crawler with multiple fallback strategies"""
    print("[crawler] Starting enhanced crawler...")
    
    # Start with manual URLs and discovered URLs
    queue: Set[str] = set(START_URLS)
    queue.update(get_manual_urls())
    
    # Try to parse sitemaps (but don't rely on them completely)
    for root in START_URLS:
        try:
            sitemap_urls = parse_sitemaps(root)
            queue.update(sitemap_urls)
            print(f"[crawler] Found {len(sitemap_urls)} URLs from sitemaps")
        except Exception as e:
            print(f"[crawler] Sitemap parsing error for {root}: {e}")
    
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
                title, text = extract_text_enhanced(resp.content, url)
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
        
        # Discover more links from HTML pages
        if kind == "html":
            try:
                new_links = discover_links_enhanced(resp.text, url)
                for u in new_links:
                    if u not in seen and u not in queue:
                        queue.add(u)
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

def parse_sitemaps(root: str) -> Set[str]:
    """Parse sitemaps and return URLs"""
    urls = set()
    for path in ("/sitemap.xml", "/sitemap_index.xml", "/sitemap/"):
        s = urljoin(root, path)
        try:
            r = session.get(s)
            if r.status_code != 200:
                continue
            if b"<urlset" in r.content or b"<sitemapindex" in r.content:
                soup = BeautifulSoup(r.text, "xml")
                for loc in soup.find_all("loc"):
                    u = canonicalize(loc.text.strip())
                    if u.endswith(".xml"):
                        # This is a sitemap, try to parse it
                        try:
                            sub = session.get(u)
                            if sub.status_code == 200:
                                soup2 = BeautifulSoup(sub.text, "xml")
                                for loc2 in soup2.find_all("loc"):
                                    uu = canonicalize(loc2.text.strip())
                                    if allowed(uu): 
                                        urls.add(uu)
                        except Exception:
                            pass
                    else:
                        if allowed(u): 
                            urls.add(u)
        except Exception:
            pass
    return urls

if __name__ == "__main__":
    crawl_enhanced()

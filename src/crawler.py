import os, time, httpx
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from langdetect import detect, DetectorFactory
from simhash import Simhash
import json
from typing import Set, List

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

def parse_sitemaps(root: str) -> Set[str]:
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
                        sub = session.get(u)
                        if sub.status_code == 200:
                            soup2 = BeautifulSoup(sub.text, "xml")
                            for loc2 in soup2.find_all("loc"):
                                uu = canonicalize(loc2.text.strip())
                                if allowed(uu): urls.add(uu)
                    else:
                        if allowed(u): urls.add(u)
        except Exception:
            pass
    return urls

def discover_links(html: str, base_url: str) -> Set[str]:
    soup = BeautifulSoup(html, "lxml")
    links = set()
    for a in soup.select("a[href]"):
        u = urljoin(base_url, a["href"])
        if allowed(u):
            links.add(canonicalize(u))
    return links

def crawl():
    queue: Set[str] = set(START_URLS)
    for root in START_URLS:
        for u in parse_sitemaps(root):
            queue.add(u)

    seen: Set[str] = set()
    out_rows: List[dict] = []
    content_hashes: Set[int] = set()
    pages = 0

    while queue and pages < CRAWL_MAX_PAGES:
        url = queue.pop()
        if not allowed(url): continue
        url = canonicalize(url)
        if url in seen: continue
        seen.add(url)

        try:
            time.sleep(CRAWL_RATE_SECONDS)
            resp = session.get(url)
        except Exception:
            continue
        if resp.status_code != 200 or not resp.content: continue

        ctype = resp.headers.get("Content-Type", "").lower()
        last_mod = resp.headers.get("Last-Modified", "")
        title, text, kind = "", "", "other"

        if "pdf" in ctype or url.lower().endswith(".pdf"):
            kind = "pdf"
            try: text = extract_text_from_pdf(resp.content)
            except Exception: text = ""
        elif "html" in ctype or url.lower().endswith((".html", ".htm", "/")):
            kind = "html"
            try: title, text = extract_text_from_html(resp.content)
            except Exception: text = ""
        else:
            continue

        if not text or len(text) < 100: continue

        # Language: URL hint + detector
        lang = "ar" if "/ar/" in url else "en"
        try:
            det = detect(text[:2000])
            if det.startswith("ar"): lang = "ar"
            elif det.startswith("en"): lang = "en"
        except Exception:
            pass

        # Near-duplicate drop with SimHash
        sh = Simhash(text).value
        if any(bin(prev ^ sh).count("1") <= 3 for prev in content_hashes):
            continue
        content_hashes.add(sh)

        # Chunk and stage
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
        if kind == "html":
            try:
                for u in discover_links(resp.text, url):
                    if u not in seen: queue.add(u)
            except Exception:
                pass

    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "data"), exist_ok=True)
    out_path = os.path.join(os.path.dirname(__file__), "..", "data", "university_corpus.jsonl")
    with open(out_path, "w", encoding="utf-8") as f:
        for row in out_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"[crawler] Wrote {len(out_rows)} chunks from {pages} pages to {out_path}")

if __name__ == "__main__":
    crawl()

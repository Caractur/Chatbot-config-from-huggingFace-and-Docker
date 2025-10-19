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

def test_basic_connection():
    print("=== Testing Basic Connection ===")
    for url in START_URLS:
        try:
            print(f"Testing URL: {url}")
            resp = session.get(url)
            print(f"Status: {resp.status_code}")
            print(f"Content-Type: {resp.headers.get('Content-Type', 'Unknown')}")
            print(f"Content length: {len(resp.content)}")
            print(f"Title: {BeautifulSoup(resp.text, 'lxml').title.text if BeautifulSoup(resp.text, 'lxml').title else 'No title'}")
            print("---")
        except Exception as e:
            print(f"Error with {url}: {e}")
            print("---")

def test_text_extraction():
    print("\n=== Testing Text Extraction ===")
    for url in START_URLS:
        try:
            print(f"Testing text extraction from: {url}")
            resp = session.get(url)
            if resp.status_code == 200:
                title, text = extract_text_from_html(resp.content)
                print(f"Extracted title: {title}")
                print(f"Extracted text length: {len(text)}")
                print(f"First 200 chars: {text[:200]}")
                print("---")
        except Exception as e:
            print(f"Error extracting text from {url}: {e}")
            print("---")

def test_link_discovery():
    print("\n=== Testing Link Discovery ===")
    for url in START_URLS:
        try:
            print(f"Testing link discovery from: {url}")
            resp = session.get(url)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'lxml')
                links = soup.find_all('a', href=True)
                print(f"Found {len(links)} links")
                for i, link in enumerate(links[:10]):  # Show first 10 links
                    href = link.get('href')
                    text = link.get_text(strip=True)
                    print(f"  {i+1}. {href} - {text}")
                print("---")
        except Exception as e:
            print(f"Error discovering links from {url}: {e}")
            print("---")

def test_sitemap_parsing():
    print("\n=== Testing Sitemap Parsing ===")
    for root in START_URLS:
        print(f"Testing sitemap for: {root}")
        for path in ("/sitemap.xml", "/sitemap_index.xml", "/sitemap/"):
            s = urljoin(root, path)
            try:
                r = session.get(s)
                print(f"  {path}: Status {r.status_code}, Length {len(r.content)}")
                if r.status_code == 200:
                    if b"<urlset" in r.content or b"<sitemapindex" in r.content:
                        print(f"    Valid sitemap found!")
                    else:
                        print(f"    Not a valid sitemap")
            except Exception as e:
                print(f"    Error: {e}")
        print("---")

if __name__ == "__main__":
    print(f"Configuration:")
    print(f"ALLOWED_DOMAINS: {ALLOWED_DOMAINS}")
    print(f"START_URLS: {START_URLS}")
    print(f"CRAWL_MAX_PAGES: {CRAWL_MAX_PAGES}")
    print(f"USER_AGENT: {USER_AGENT}")
    print("=" * 50)
    
    test_basic_connection()
    test_text_extraction()
    test_link_discovery()
    test_sitemap_parsing()

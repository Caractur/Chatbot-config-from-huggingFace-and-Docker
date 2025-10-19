import httpx
from bs4 import BeautifulSoup
import json

def test_alternative_sources():
    """Test various alternative content sources"""
    base_url = "https://www.htu.edu.jo"
    
    # Test URLs that might contain content
    test_urls = [
        # RSS feeds
        f"{base_url}/rss.xml",
        f"{base_url}/feed.xml",
        f"{base_url}/news/rss",
        f"{base_url}/ar/news/rss",
        
        # API endpoints
        f"{base_url}/api/",
        f"{base_url}/_next/data/",
        f"{base_url}/api/news",
        f"{base_url}/api/programs",
        
        # Static content
        f"{base_url}/static/",
        f"{base_url}/public/",
        f"{base_url}/assets/",
        f"{base_url}/content/",
        
        # Alternative paths
        f"{base_url}/sitemap.xml",
        f"{base_url}/robots.txt",
        f"{base_url}/manifest.json",
        
        # Specific content areas
        f"{base_url}/about/",
        f"{base_url}/ar/about/",
        f"{base_url}/academics/",
        f"{base_url}/ar/academics/",
    ]
    
    session = httpx.Client(timeout=10, follow_redirects=True)
    
    print("Testing alternative content sources...")
    print("=" * 50)
    
    for url in test_urls:
        try:
            print(f"\nTesting: {url}")
            resp = session.get(url)
            print(f"Status: {resp.status_code}")
            print(f"Content-Type: {resp.headers.get('Content-Type', 'Unknown')}")
            print(f"Content length: {len(resp.content)}")
            
            if resp.status_code == 200 and resp.content:
                # Check if it's HTML
                if "text/html" in resp.headers.get("Content-Type", ""):
                    soup = BeautifulSoup(resp.text, "lxml")
                    title = soup.title.text if soup.title else "No title"
                    print(f"Title: {title}")
                    
                    # Look for actual content
                    content_selectors = [
                        "main", "[role='main']", ".main", "#main", 
                        ".content", "#content", "article", ".article"
                    ]
                    
                    for selector in content_selectors:
                        elements = soup.select(selector)
                        if elements:
                            for element in elements:
                                text = element.get_text(strip=True)
                                if len(text) > 100:
                                    print(f"Found content in {selector}: {len(text)} chars")
                                    print(f"Preview: {text[:200]}...")
                                    break
                
                # Check if it's JSON (API response)
                elif "application/json" in resp.headers.get("Content-Type", ""):
                    try:
                        data = resp.json()
                        print(f"JSON response: {type(data)}")
                        if isinstance(data, dict):
                            print(f"Keys: {list(data.keys())}")
                        elif isinstance(data, list):
                            print(f"List with {len(data)} items")
                    except:
                        print("Invalid JSON")
                
                # Check if it's XML (RSS, sitemap)
                elif "xml" in resp.headers.get("Content-Type", ""):
                    print("XML content detected")
                    if b"<rss" in resp.content:
                        print("RSS feed found!")
                    elif b"<urlset" in resp.content:
                        print("Sitemap found!")
                
                # Check if it's plain text
                elif "text/plain" in resp.headers.get("Content-Type", ""):
                    print(f"Plain text: {resp.text[:200]}...")
                
            elif resp.status_code == 404:
                print("Not found")
            elif resp.status_code == 403:
                print("Forbidden")
            elif resp.status_code == 500:
                print("Server error")
            
        except Exception as e:
            print(f"Error: {e}")
        
        print("-" * 30)

if __name__ == "__main__":
    test_alternative_sources()

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def normalize_url(url):
    """Remove trailing slash and index.html to avoid duplicate pages"""
    url = url.rstrip('/')
    if url.endswith('/index.html'):
        url = url[:-len('/index.html')]
    return url

def crawl_website(start_url, max_pages=30):
    """
    Given a starting URL, crawl all internal pages on the same domain.
    Returns a list of dicts: [{url, text}, {url, text}, ...]
    """
    visited = set()
    to_visit = [normalize_url(start_url)]
    pages = []

    # Extract domain so we only crawl pages on the same website
    domain = urlparse(start_url).netloc

    # Pretend to be a browser so websites don't block us
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    print(f"Starting crawl on: {start_url}")
    print(f"Domain: {domain}")

    while to_visit and len(visited) < max_pages:
        url = normalize_url(to_visit.pop(0))

        # Skip if already visited
        if url in visited:
            continue

        try:
            # Fetch the page
            response = requests.get(url, headers=headers, timeout=10, verify=False)

            # Skip non-HTML pages (PDFs, images etc)
            if 'text/html' not in response.headers.get('Content-Type', ''):
                continue

            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove script and style tags — we don't want that text
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()

            # Extract clean text
            text = ' '.join(soup.get_text().split())

            # Only save pages that have meaningful content
            if len(text) > 100:
                pages.append({
                    'url': url,
                    'text': text
                })
                print(f"Crawled [{len(pages)}]: {url} — {len(text)} chars")

            # Find all links on this page
            for a_tag in soup.find_all('a', href=True):
                full_url = normalize_url(urljoin(url, a_tag['href']))
                parsed = urlparse(full_url)

                # Only follow links on the same domain
                # Skip anchors, mailto links
                if (parsed.netloc == domain and
                    full_url not in visited and
                    full_url not in to_visit and
                    '#' not in full_url and
                    'mailto' not in full_url):
                    to_visit.append(full_url)

            visited.add(url)

        except Exception as e:
            print(f"Failed to crawl {url}: {e}")
            visited.add(url)

    print(f"\nCrawl complete. Pages collected: {len(pages)}")
    return pages


# ---- TEST BLOCK ----
if __name__ == "__main__":
    test_url = "https://books.toscrape.com"
    results = crawl_website(test_url, max_pages=5)

    print("\n--- RESULTS ---")
    for page in results:
        print(f"\nURL: {page['url']}")
        print(f"Text preview: {page['text'][:200]}...")
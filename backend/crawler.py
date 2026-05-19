"""
crawler.py -- Day 4+5 & Day 6: Botkit Mini
-----------------------------------
Crawls websites using requests+BeautifulSoup (fast) with Playwright
as a fallback for JS-heavy sites (React, Next.js, etc).

Preserves page structure (markdown), titles, and descriptions for advanced RAG context.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import urllib3
import markdownify

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Try to import Playwright — it's optional
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("[crawler] WARNING: Playwright not installed. JS-heavy sites may not crawl properly.")
    print("[crawler] Install with: pip install playwright && playwright install chromium")


def normalize_url(url):
    """Remove trailing slash and index.html to avoid duplicate pages"""
    url = url.rstrip('/')
    if url.endswith('/index.html'):
        url = url[:-len('/index.html')]
    return url


def extract_metadata(soup):
    """Extract page title and meta description for context enrichment"""
    title = ""
    description = ""
    if soup:
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        
        desc_tag = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
        if desc_tag and desc_tag.get('content'):
            description = desc_tag.get('content').strip()
    return title, description


def html_to_clean_markdown(html_content):
    """Convert HTML content to clean, readable markdown format"""
    if not html_content:
        return ""
    try:
        temp_soup = BeautifulSoup(html_content, 'html.parser')
        # Strip script/style/nav/footer/header for clean content markdown
        for tag in temp_soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()
        md = markdownify.markdownify(str(temp_soup), heading_style="ATX")
        # Clean empty lines
        lines = [line.strip() for line in md.split('\n') if line.strip()]
        return '\n'.join(lines)
    except Exception as e:
        print(f"[crawler] Markdown conversion error: {e}")
        return ""


def crawl_page_with_playwright(url):
    """
    Fallback crawler for JS-heavy websites.
    Opens a real Chromium browser (headless), waits for JS to render,
    then extracts text, full rendered HTML, title, and description.
    """
    if not PLAYWRIGHT_AVAILABLE:
        print(f"[playwright] Skipped {url} -- Playwright not installed")
        return "", "", "", ""

    print(f"[playwright] Rendering JS page: {url}")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            
            title = page.title() or ""
            
            # Attempt to extract meta description
            description = ""
            try:
                description = page.locator('meta[name="description"]').get_attribute('content') or ""
            except Exception:
                try:
                    description = page.locator('meta[property="og:description"]').get_attribute('content') or ""
                except Exception:
                    pass

            # Remove navigation, footers, headers, scripts, and styles before getting text
            page.evaluate("""
                () => {
                    ['nav','footer','header','script','style']
                    .forEach(tag => document.querySelectorAll(tag)
                    .forEach(el => el.remove()))
                }
            """)
            text = page.inner_text('body')
            text = ' '.join(text.split())
            
            html_content = page.content()
            browser.close()
            print(f"[playwright] Got {len(text)} chars from {url}")
            return text, html_content, title, description
    except Exception as e:
        print(f"[playwright] Failed on {url}: {e}")
        return "", "", "", ""


def crawl_website(start_url, max_pages=30):
    """
    Given a starting URL, crawl all internal pages on the same domain.
    Returns a list of dicts: [{url, text, title, description, markdown}, ...]
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
            # Fetch the page with requests (fast method)
            response = requests.get(url, headers=headers, timeout=10, verify=False)

            # Skip non-HTML pages (PDFs, images etc)
            if 'text/html' not in response.headers.get('Content-Type', ''):
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            title, description = extract_metadata(soup)
            html_content = response.text

            # Remove script and style tags -- we don't want that text
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()

            # Extract clean text
            text = ' '.join(soup.get_text().split())
            method = "requests"

            # Day 4+5: If BeautifulSoup got very little text, try Playwright
            if len(text) < 200 and PLAYWRIGHT_AVAILABLE:
                print(f"[crawler] Low content ({len(text)} chars), trying Playwright...")
                pw_text, pw_html, pw_title, pw_desc = crawl_page_with_playwright(url)
                if len(pw_text) > len(text):
                    text = pw_text
                    html_content = pw_html
                    if pw_title:
                        title = pw_title
                    if pw_desc:
                        description = pw_desc
                    method = "playwright"

            # Generate clean markdown from HTML content
            markdown = html_to_clean_markdown(html_content)
            if not markdown:
                markdown = text

            # Only save pages that have meaningful content
            if len(text) > 100:
                pages.append({
                    'url': url,
                    'text': text,
                    'title': title,
                    'description': description,
                    'markdown': markdown
                })
                print(f"Crawled [{len(pages)}]: {url} -- {len(text)} chars ({method})")

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
            print(f"Failed {url}: {e} — retrying once...")
            try:
                response = requests.get(url, headers=headers,
                                        timeout=15, verify=False)
                soup = BeautifulSoup(response.text, 'html.parser')
                title, description = extract_metadata(soup)
                html_content = response.text
                
                for tag in soup(['script','style','nav','footer','header']):
                    tag.decompose()
                text = ' '.join(soup.get_text().split())
                
                markdown = html_to_clean_markdown(html_content)
                if not markdown:
                    markdown = text
                
                if len(text) > 100:
                    pages.append({
                        'url': url,
                        'text': text,
                        'title': title,
                        'description': description,
                        'markdown': markdown
                    })
                    print(f"Retry succeeded: {url}")
            except Exception as e2:
                print(f"Retry also failed {url}: {e2}")
            visited.add(url)

    print(f"\nCrawl complete. Pages collected: {len(pages)}")
    return pages


# ---- TEST BLOCK ----
if __name__ == "__main__":
    import sys

    # Default test: books.toscrape.com (static site, uses requests)
    test_url = "https://books.toscrape.com"
    max_p = 5

    # Allow command-line override for testing JS sites
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    if len(sys.argv) > 2:
        max_p = int(sys.argv[2])

    print(f"\n{'='*60}")
    print(f"  CRAWLER TEST -- {test_url}")
    print(f"  Playwright available: {PLAYWRIGHT_AVAILABLE}")
    print(f"{'='*60}\n")

    results = crawl_website(test_url, max_pages=max_p)

    print("\n--- RESULTS ---")
    for page in results:
        print(f"\nURL: {page['url']}")
        print(f"Title: {page.get('title')}")
        print(f"Description: {page.get('description')}")
        print(f"Markdown preview:\n{page.get('markdown')[:200]}...")

    print(f"\nTotal pages crawled: {len(results)}")
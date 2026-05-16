"""
crawler.py — Web Content Fetcher for BotKit India
Fetches a URL, extracts clean text content using BeautifulSoup,
and returns structured data ready for embedding.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from datetime import datetime
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Tags to remove — these contain navigation, ads, footers, etc.
REMOVE_TAGS = [
    "script", "style", "nav", "footer", "header", "aside",
    "form", "button", "iframe", "noscript", "svg", "img",
    "video", "audio", "canvas", "map", "figure"
]

# Class/ID patterns that typically contain non-content elements
REMOVE_PATTERNS = [
    r"nav", r"menu", r"sidebar", r"footer", r"header",
    r"comment", r"advert", r"social", r"share", r"cookie",
    r"popup", r"modal", r"banner", r"promo"
]


def fetch_page(url: str, timeout: int = 15) -> str | None:
    """
    Fetch raw HTML from a URL.
    
    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds
        
    Returns:
        Raw HTML string or None if fetch failed
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    try:
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()

        # Ensure we got HTML, not a PDF or image
        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type and "application/xhtml" not in content_type:
            logger.warning(f"Non-HTML content type: {content_type} for {url}")
            return None

        response.encoding = response.apparent_encoding or "utf-8"
        return response.text

    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching {url}")
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error for {url}")
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error {e.response.status_code} for {url}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed for {url}: {e}")

    return None


def _should_remove_element(element) -> bool:
    """Check if an element matches removal patterns based on class/id."""
    if not hasattr(element, "attrs") or element.attrs is None:
        return False

    classes = element.get("class", [])
    if isinstance(classes, list):
        classes = " ".join(classes)
        
    elem_id = element.get("id", "")
    if isinstance(elem_id, list):
        elem_id = " ".join(elem_id)
        
    combined = f"{classes} {elem_id}".lower()

    for pattern in REMOVE_PATTERNS:
        if re.search(pattern, combined):
            return True
    return False


def extract_text(html: str) -> str:
    """
    Parse HTML and extract clean, readable text content.
    Removes navigation, ads, footers, scripts, and other non-content elements.
    
    Args:
        html: Raw HTML string
        
    Returns:
        Clean text content
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove unwanted tags entirely
    for tag_name in REMOVE_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # Remove elements matching non-content patterns
    for element in soup.find_all(True):
        if _should_remove_element(element):
            element.decompose()

    # Try to find the main content area first
    main_content = (
        soup.find("main")
        or soup.find("article")
        or soup.find("div", {"role": "main"})
        or soup.find("div", class_=re.compile(r"content|article|post|entry", re.I))
        or soup.body
        or soup
    )

    # Extract text with proper spacing
    text = main_content.get_text(separator="\n", strip=True)

    # Clean up the text
    # Remove excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove lines that are just whitespace
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    text = "\n".join(lines)

    return text


def extract_title(html: str) -> str:
    """Extract the page title from HTML."""
    soup = BeautifulSoup(html, "html.parser")

    # Try og:title first (usually the best)
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        return og_title["content"].strip()

    # Try <title> tag
    if soup.title and soup.title.string:
        return soup.title.string.strip()

    # Try first h1
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)

    return "Untitled Page"


def crawl(url: str) -> dict | None:
    """
    Main crawl function — fetches a URL and returns structured data.
    
    Args:
        url: The URL to crawl
        
    Returns:
        Dictionary with url, title, text, domain, timestamp
        or None if crawl failed
    """
    logger.info(f"🕷️ Crawling: {url}")

    # Validate URL
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        logger.error(f"Invalid URL: {url}")
        return None

    # Fetch the page
    html = fetch_page(url)
    if not html:
        return None

    # Extract content
    text = extract_text(html)
    title = extract_title(html)

    # Validate — need meaningful content
    if len(text) < 50:
        logger.warning(f"Too little content extracted from {url} ({len(text)} chars)")
        return None

    result = {
        "url": url,
        "title": title,
        "text": text,
        "domain": parsed.netloc,
        "timestamp": datetime.utcnow().isoformat(),
        "char_count": len(text),
    }

    logger.info(f"✅ Crawled: {title} ({len(text)} chars)")
    return result


if __name__ == "__main__":
    # Quick test
    test_url = input("Enter a URL to crawl: ").strip()
    result = crawl(test_url)
    if result:
        print(f"\n--- {result['title']} ---")
        print(f"Domain: {result['domain']}")
        print(f"Characters: {result['char_count']}")
        print(f"\nFirst 500 chars:\n{result['text'][:500]}")
    else:
        print("Crawl failed.")

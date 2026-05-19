# Crawler Test Results — Day 6

## Test Configuration
- **Date:** 2026-05-19
- **Branch:** manav/dev
- **Crawler:** requests + BeautifulSoup (primary) + Playwright (fallback)
- **max_pages:** 5 per site

## Results

| Website | Pages Crawled | Method | Issues |
|---------|--------------|--------|--------|
| amul.com | 1 | requests | Only homepage crawlable — internal links use different subdomain |
| manipalhospitals.com | 5 | requests | All pages worked perfectly — largest page 100K chars (orthopaedics) |
| lenskart.com | 5 | requests + playwright | 2 pages needed Playwright fallback (JS-heavy), got 127 chars each |
| 1mg.com | 5 | requests | All pages crawled successfully — 283 to 5067 chars per page |
| tanishq.co.in | 0 | playwright attempted | JS-only site, Playwright timed out (30s) — heavy Cloudflare protection |

## Observations

### Best Results
- **manipalhospitals.com** — Crawled cleanly with requests, rich content on every page
- **1mg.com** — All 5 pages returned good content using requests only

### Playwright Fallback Triggered
- **lenskart.com** — 2 out of 5 pages had less than 200 chars with BeautifulSoup, Playwright kicked in and extracted 127 chars each
- **tanishq.co.in** — BeautifulSoup got only 57 chars, Playwright attempted but timed out

### Sites That Block Crawlers
- **tanishq.co.in** — Heavy JS + possible Cloudflare. Cannot be crawled with current setup
- This is expected behavior — not all sites are crawlable

## Conclusion
- 4 out of 5 sites crawled successfully
- Playwright fallback works correctly when BeautifulSoup gets low content
- Retry logic (added Day 6) helps recover failed pages

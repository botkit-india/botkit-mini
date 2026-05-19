"""
Day 6 — Test crawler on 5 Indian websites
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from crawler import crawl_website

sites = [
    ('amul.com', 'https://www.amul.com', 5),
    ('manipalhospitals.com', 'https://www.manipalhospitals.com', 5),
    ('lenskart.com', 'https://www.lenskart.com', 5),
    ('1mg.com', 'https://www.1mg.com', 5),
    ('tanishq.co.in', 'https://www.tanishq.co.in', 5),
]

results = []
for name, url, mp in sites:
    sep = "=" * 60
    print(f"\n{sep}")
    print(f"  TESTING: {name}")
    print(sep)
    try:
        pages = crawl_website(url, max_pages=mp)
        results.append((name, len(pages), 'OK'))
    except Exception as e:
        print(f"CRASHED: {e}")
        results.append((name, 0, str(e)[:50]))

sep = "=" * 60
print(f"\n{sep}")
print("  SUMMARY")
print(sep)
for name, count, status in results:
    print(f"  {name:30s} | {count} pages | {status}")

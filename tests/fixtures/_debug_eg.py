"""Debug why ExhibitionGlobeScraper finds 0 cards."""
from utils.helpers import site_selectors
from scrapers.exhibition_globe import ExhibitionGlobeScraper
from bs4 import BeautifulSoup

print("=" * 70)
print("1. WHAT SELECTORS.YAML ACTUALLY LOADS")
print("=" * 70)
sel = site_selectors("exhibition_globe")
for key, value in sel.items():
    print(f"  {key}: {value!r}")

print()
print("=" * 70)
print("2. WHAT THE SCRAPER LOOKS FOR")
print("=" * 70)
with ExhibitionGlobeScraper() as s:
    print(f"  BASE_URL          : {s.BASE_URL}")
    print(f"  event_card        : {s.sel.get('event_card')!r}")
    print(f"  search_queries    : {s.sel.get('search_queries')!r}")
    print(f"  search_url_template: {s.sel.get('search_url_template')!r}")

    template = s.sel.get("search_url_template", "https://exhibitionglobe.com/?s={query}")
    queries = s.sel.get("search_queries", [])

    print()
    print("=" * 70)
    print("3. TRY FETCHING ONE SEARCH URL")
    print("=" * 70)

    if not queries:
        print("  ❌ search_queries is EMPTY — falling back to default")
        queries = ["ahmedabad"]

    url = s._build_search_url(template, queries[0], 1)
    print(f"  URL: {url}")

    try:
        html = s.fetch(url)
        print(f"  Bytes: {len(html)}")

        soup = BeautifulSoup(html, "lxml")
        print(f"  <title>: {soup.title.get_text(strip=True) if soup.title else '?'}")

        # Count with several selectors
        for css in [".e-loop-item", "article", ".hentry", "h2 a", "a"]:
            count = len(soup.select(css))
            print(f"  {css:20} → {count} matches")

        # Show first 3 <a> hrefs that look like event links
        print("\n  First 5 links with 'expo' or 'news' in href:")
        shown = 0
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if any(k in href.lower() for k in ("expo", "news", "exhibition")):
                print(f"    {a.get_text(strip=True)[:50]!r}")
                print(f"      → {href}")
                shown += 1
                if shown >= 5:
                    break

    except Exception as e:
        print(f"  ❌ Fetch failed: {type(e).__name__}: {e}")
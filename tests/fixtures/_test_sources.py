"""
Diagnostic — tries 3 friendly sources and reports which are scrapable.
Run: python -m tests.fixtures._test_sources
"""
from scrapers.base_scraper import BaseScraper, FetchError

# Candidate sources to test
SOURCES = [
    {
        "name": "exhibition_globe",
        "url":  "https://www.exhibitionglobe.com/trade-shows/india",
    },
    {
        "name": "expolume",
        "url":  "https://www.expolume.com/expos/india",
    },
    {
        "name": "mera_events",
        "url":  "https://www.meraevents.com/",
    },
    {
        "name": "itpo",
        "url":  "https://www.indiatradefair.com/",
    },
    {
        "name": "10times_sitemap",  # ← test if sitemap is accessible
        "url":  "https://10times.com/xml/sitemaps.xml",
    },
]


class Probe(BaseScraper):
    SITE_NAME = "probe"
    BASE_URL = ""


with Probe() as s:
    print(f"{'SOURCE':<20} {'STATUS':<10} {'BYTES':>8}  TITLE")
    print("=" * 80)

    for src in SOURCES:
        name, url = src["name"], src["url"]
        try:
            html = s.fetch(url, allow_robots_bypass=True)  # diagnostic only
            title = ""
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, "lxml")
                if soup.title:
                    title = soup.title.get_text(strip=True)[:50]
            except Exception:
                pass
            print(f"{name:<20} {'✅ OK':<10} {len(html):>8}  {title}")
        except FetchError as e:
            msg = str(e)[:60]
            print(f"{name:<20} {'❌ FAIL':<10} {'—':>8}  {msg}")
        except Exception as e:
            print(f"{name:<20} {'❌ ERR':<10} {'—':>8}  {type(e).__name__}: {str(e)[:50]}")
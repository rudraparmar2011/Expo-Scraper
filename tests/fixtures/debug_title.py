"""Debug why example.com's title isn't extracted."""
from scrapers.base_scraper import BaseScraper
from bs4 import BeautifulSoup

class D(BaseScraper):
    SITE_NAME = "debug"
    BASE_URL = "https://example.com"

with D() as s:
    html = s.fetch("https://example.com")

    print("=" * 60)
    print("HTML length   :", len(html))
    print("First 400 chars:")
    print("-" * 60)
    print(html[:400])
    print("-" * 60)

    soup = BeautifulSoup(html, "lxml")

    print("\n[soup.title]                :", repr(soup.title))
    print("[soup.title.string]         :", repr(soup.title.string if soup.title else None))
    print("[soup.title.get_text()]     :", repr(soup.title.get_text(strip=True) if soup.title else None))
    print("[soup.find('title')]        :", repr(soup.find("title")))
    print("[find('title').text]        :", repr(soup.find("title").text.strip() if soup.find("title") else None))

    print("\nAll <title> tags found      :", soup.find_all("title"))
    print("Total tags in soup          :", len(soup.find_all()))

    # Check encoding
    print("\n--- encoding info ---")
    print("response.encoding set to    :", s.session.get("https://example.com").encoding)
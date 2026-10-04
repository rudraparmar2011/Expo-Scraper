"""
Probe multiple sources for Ahmedabad/Vadodara event listings.

Run: python -m tests.fixtures._probe_cities
"""
from bs4 import BeautifulSoup
from scrapers.base_scraper import BaseScraper, FetchError


PROBES = [
    # ---------- MeraEvents (India, all event types) ----------
    ("meraevents",  "https://www.meraevents.com/events/ahmedabad"),
    ("meraevents",  "https://www.meraevents.com/events/vadodara"),
    ("meraevents",  "https://www.meraevents.com/ahmedabad"),
    ("meraevents",  "https://www.meraevents.com/vadodara"),

    # ---------- Allevents.in (all Indian events) ----------
    ("allevents",   "https://allevents.in/ahmedabad"),
    ("allevents",   "https://allevents.in/vadodara"),

    # ---------- Expolume (expos only) ----------
    ("expolume",    "https://www.expolume.com/expos/india/ahmedabad"),
    ("expolume",    "https://www.expolume.com/expos/india/vadodara"),
    ("expolume",    "https://www.expolume.com/expos/ahmedabad"),
    ("expolume",    "https://www.expolume.com/expos/vadodara"),

    # ---------- Exhibition Globe (keyword search) ----------
    ("exhibitionglobe", "https://exhibitionglobe.com/?s=ahmedabad"),
    ("exhibitionglobe", "https://exhibitionglobe.com/?s=vadodara"),
    ("exhibitionglobe", "https://exhibitionglobe.com/?s=ahmedabad+expo"),
    ("exhibitionglobe", "https://exhibitionglobe.com/?s=vadodara+expo"),

    # ---------- 10times city pages (might be less protected) ----------
    ("10times",     "https://10times.com/ahmedabad"),
    ("10times",     "https://10times.com/vadodara"),
]


# Common card selectors to try per source
CARD_SELECTORS = {
    "meraevents":       [".event-box", ".event-card", ".ev-card", "article", ".card"],
    "allevents":        [".event-item", ".evt-card", "article", ".event-card"],
    "expolume":         [".expo-card", ".event-card", ".card", "article"],
    "exhibitionglobe":  [".e-loop-item", "article", ".hentry"],
    "10times":          ["#listing-events > tbody > tr.Box", ".event-card"],
}


def probe(source: str, url: str) -> dict:
    """Fetch URL and report what was found."""
    result = {
        "source": source,
        "url": url,
        "status": "?",
        "bytes": 0,
        "title": "",
        "cards": 0,
        "sample_titles": [],
    }

    with BaseScraper() as s:
        s.BASE_URL = "https://" + url.split("/")[2]
        try:
            html = s.fetch(url, allow_robots_bypass=True)
            result["bytes"] = len(html)
            result["status"] = "OK"

            soup = BeautifulSoup(html, "lxml")
            if soup.title:
                result["title"] = soup.title.get_text(strip=True)[:55]

            # Try each candidate selector
            for sel in CARD_SELECTORS.get(source, []):
                cards = soup.select(sel)
                if len(cards) >= 3:  # at least 3 cards = likely a listing
                    result["cards"] = len(cards)

                    # Extract first 3 titles
                    for card in cards[:3]:
                        # Try common title tags
                        for tag in ("h2", "h3", "h4"):
                            title_el = card.find(tag)
                            if title_el:
                                text = title_el.get_text(strip=True)[:60]
                                if text:
                                    result["sample_titles"].append(text)
                                    break
                    break
        except FetchError as e:
            result["status"] = f"HTTP FAIL"
            result["title"] = str(e)[:50]
        except Exception as e:
            result["status"] = type(e).__name__
            result["title"] = str(e)[:50]

    return result


if __name__ == "__main__":
    print(f"{'SOURCE':<18} {'STATUS':<12} {'BYTES':>8} {'CARDS':>6}  URL")
    print("=" * 100)

    hits = []
    for source, url in PROBES:
        r = probe(source, url)
        marker = "🎯" if r["cards"] >= 5 else ("✅" if r["status"] == "OK" else "❌")
        print(f"{marker} {r['source']:<16} {r['status']:<12} {r['bytes']:>8} {r['cards']:>6}  {r['url']}")
        if r["title"]:
            print(f"   └─ title: {r['title']}")
        for t in r["sample_titles"][:2]:
            print(f"   └─ {t}")
        if r["cards"] >= 5:
            hits.append(r)

    print("\n" + "=" * 100)
    print(f"🎯 {len(hits)} sources with real listings found:")
    for h in hits:
        print(f"   ✅ {h['source']:<18} {h['url']}  ({h['cards']} cards)")
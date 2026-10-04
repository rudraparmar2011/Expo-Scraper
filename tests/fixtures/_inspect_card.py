"""
Deep-inspect the actual event card structure in Exhibition Globe.

Run: python -m tests.fixtures._inspect_card
"""
from bs4 import BeautifulSoup
from scrapers.base_scraper import BaseScraper
from urllib.parse import urljoin


TARGET_URL = "https://www.exhibitionglobe.com/trade-shows/india"


class Inspector(BaseScraper):
    SITE_NAME = "inspector"
    BASE_URL = "https://www.exhibitionglobe.com"


def dump_html(elem, indent=0, max_depth=8):
    """Pretty-print an HTML tree with attributes."""
    if indent > max_depth:
        return
    pad = "  " * indent
    classes = " ".join(elem.get("class", []))
    eid = f"#{elem.get('id')}" if elem.get("id") else ""
    cls_str = f".{classes.replace(' ', '.')}" if classes else ""

    # Show other important attrs
    extra = ""
    for attr in ("href", "src", "data-id"):
        if elem.get(attr):
            extra += f'  {attr}="{str(elem[attr])[:60]}"'

    # Text preview
    text = elem.get_text(" ", strip=True)[:50]
    text_str = f"  → {text!r}" if text else ""

    print(f"{pad}<{elem.name}{eid}{cls_str}>{extra}{text_str}")

    for child in elem.children:
        if hasattr(child, "name") and child.name:
            dump_html(child, indent + 1, max_depth)


with Inspector() as s:
    print(f"Fetching {TARGET_URL} ...\n")
    soup = s.soup(TARGET_URL)

    # ------------------------------------------------------------------
    # 1. Find all e-loop-item cards
    # ------------------------------------------------------------------
    cards = soup.select(".e-loop-item")
    print(f"Found {len(cards)} cards with .e-loop-item\n")

    # Also try alternative selectors
    print("Card count by selector:")
    for sel in [".e-loop-item", ".hentry", ".status-publish",
                "article", ".elementor-post", ".type-exhibition",
                "div[class*='loop']"]:
        print(f"  {sel:35} → {len(soup.select(sel))}")

    if not cards:
        print("\n❌ No .e-loop-item found. Trying .hentry...")
        cards = soup.select(".hentry")

    if not cards:
        print("❌ No cards found at all. Dumping first 3 <article> tags...")
        for art in soup.find_all("article")[:3]:
            print()
            dump_html(art, max_depth=3)
        raise SystemExit(0)

    # ------------------------------------------------------------------
    # 2. Dump the FULL structure of the FIRST card
    # ------------------------------------------------------------------
    print()
    print("=" * 78)
    print("FULL STRUCTURE OF FIRST EVENT CARD")
    print("=" * 78)
    dump_html(cards[0], max_depth=8)

    # ------------------------------------------------------------------
    # 3. Extract likely fields from first 3 cards
    # ------------------------------------------------------------------
    print()
    print("=" * 78)
    print("FIELD EXTRACTION TEST (first 3 cards)")
    print("=" * 78)

    for i, card in enumerate(cards[:3], 1):
        print(f"\n--- Card {i} ---")

        # Title: try common patterns
        title = (
            card.select_one(".elementor-post__title a")
            or card.select_one("h2 a, h3 a, h4 a, h5 a")
            or card.select_one(".elementor-heading-title a")
            or card.select_one("a[rel='bookmark']")
        )
        print(f"  title : {title.get_text(strip=True) if title else None!r}")
        print(f"  link  : {title.get('href') if title else None}")

        # Image
        img = card.select_one("img")
        if img:
            src = img.get("src") or img.get("data-src") or img.get("srcset", "").split()[0]
            print(f"  image : {src[:80] if src else None}")

        # All text (to see what other data is available)
        full_text = card.get_text(" | ", strip=True)
        print(f"  full text: {full_text[:200]}")

        # Meta / date / venue
        meta = card.select_one(".elementor-post__meta-data, .post-meta, time, .date")
        if meta:
            print(f"  meta  : {meta.get_text(strip=True)}")

        # Categories
        cats = card.select(".elementor-post__badge, .cat-links a, .category")
        if cats:
            print(f"  cats  : {[c.get_text(strip=True) for c in cats]}")

    # ------------------------------------------------------------------
    # 4. Try to find pagination
    # ------------------------------------------------------------------
    print()
    print("=" * 78)
    print("PAGINATION")
    print("=" * 78)
    for sel in [".page-numbers", ".pagination", ".elementor-pagination",
                "a.next", "a[rel='next']"]:
        elems = soup.select(sel)
        if elems:
            print(f"  {sel}  →  {len(elems)} elements")
            for e in elems[:5]:
                href = e.get("href")
                text = e.get_text(strip=True)
                print(f"      {text!r}  →  {href}")
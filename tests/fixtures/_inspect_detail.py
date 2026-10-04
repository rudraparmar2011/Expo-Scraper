"""
Inspect an Exhibition Globe detail page for structured fields.

Run: python -m tests.fixtures._inspect_detail
"""
from bs4 import BeautifulSoup
from scrapers.base_scraper import BaseScraper


# Use the first card's link from the listing
DETAIL_URL = "https://exhibitionglobe.com/latest-news/semicon-india-2026/"


class Inspector(BaseScraper):
    SITE_NAME = "inspector"
    BASE_URL = "https://exhibitionglobe.com"


def dump_html(elem, indent=0, max_depth=6):
    if indent > max_depth:
        return
    pad = "  " * indent
    classes = " ".join(elem.get("class", []))
    eid = f"#{elem.get('id')}" if elem.get("id") else ""
    cls_str = f".{classes.replace(' ', '.')}" if classes else ""

    # Extract visible text
    text = elem.get_text(" ", strip=True)[:80]
    text_str = f"  → {text!r}" if text else ""

    print(f"{pad}<{elem.name}{eid}{cls_str}>{text_str}")

    for child in elem.children:
        if hasattr(child, "name") and child.name:
            dump_html(child, indent + 1, max_depth)


with Inspector() as s:
    print(f"Fetching {DETAIL_URL} ...\n")
    soup = s.soup(DETAIL_URL)

    # ------------------------------------------------------------------
    # 1. Title
    # ------------------------------------------------------------------
    print("=" * 78)
    print("TITLE / HEADINGS")
    print("=" * 78)
    for h in soup.find_all(["h1", "h2", "h3"], limit=10):
        print(f"  <{h.name}>  {h.get_text(strip=True)[:100]}")

    # ------------------------------------------------------------------
    # 2. Look for structured metadata (dates, venue, fees)
    # ------------------------------------------------------------------
    print()
    print("=" * 78)
    print("STRUCTURED DATA (JSON-LD, meta tags)")
    print("=" * 78)

    # JSON-LD (most sites use this for SEO — very reliable!)
    import json
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            print(json.dumps(data, indent=2)[:2000])
        except Exception as e:
            print(f"  (failed to parse JSON-LD: {e})")

    # Meta tags
    print("\n--- Meta tags ---")
    for meta in soup.find_all("meta"):
        name = meta.get("property") or meta.get("name")
        content = meta.get("content", "")
        if name and any(k in name.lower() for k in ("date", "event", "location", "city", "description")):
            print(f"  {name}: {content[:100]}")

    # ------------------------------------------------------------------
    # 3. Full article body — dump the main content region
    # ------------------------------------------------------------------
    print()
    print("=" * 78)
    print("MAIN CONTENT STRUCTURE")
    print("=" * 78)

    main = (
        soup.select_one(".elementor-widget-theme-post-content")
        or soup.select_one(".entry-content")
        or soup.select_one("article")
        or soup.select_one("main")
    )
    if main:
        dump_html(main, max_depth=5)
    else:
        print("  ❌ No main content found")
        # Fallback: dump body
        print("\n--- Fallback: first 2000 chars of body text ---")
        body = soup.body
        if body:
            print(body.get_text(" ", strip=True)[:2000])

    # ------------------------------------------------------------------
    # 4. Try to find dates
    # ------------------------------------------------------------------
    print()
    print("=" * 78)
    print("DATE HUNTING")
    print("=" * 78)

    import re
    date_pattern = re.compile(
        r"\b(\d{1,2}[-–\s]\d{1,2}\s+\w{3,9}\s+\d{4}|\d{1,2}\s+\w{3,9}\s+\d{4}|\w{3,9}\s+\d{1,2}[-–]\d{1,2},?\s+\d{4})\b"
    )

    full_text = soup.get_text(" ", strip=True)
    matches = date_pattern.findall(full_text)[:10]
    if matches:
        print(f"  Found {len(matches)} date-like strings:")
        for m in matches:
            print(f"    {m}")
    else:
        print("  ❌ No date patterns found")

    # ------------------------------------------------------------------
    # 5. Time tag
    # ------------------------------------------------------------------
    times = soup.find_all("time")
    if times:
        print(f"\n  <time> tags ({len(times)}):")
        for t in times[:5]:
            print(f"    text={t.get_text(strip=True)!r}  datetime={t.get('datetime')!r}")
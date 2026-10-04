"""
Auto-inspect a page's structure to discover event-card selectors.

Run: python -m tests.fixtures._inspect_structure
"""
from collections import Counter
from bs4 import BeautifulSoup
from scrapers.base_scraper import BaseScraper


TARGET_URL = "https://www.exhibitionglobe.com/trade-shows/india"


class Inspector(BaseScraper):
    SITE_NAME = "inspector"
    BASE_URL = "https://www.exhibitionglobe.com"


def describe(elem, depth=0, max_depth=4):
    """Print a small HTML tree."""
    if depth > max_depth:
        return
    indent = "  " * depth
    classes = " ".join(elem.get("class", [])) if elem.get("class") else ""
    elem_id = f"#{elem.get('id')}" if elem.get("id") else ""
    cls_str = f".{classes.replace(' ', '.')}" if classes else ""
    text = elem.get_text(" ", strip=True)[:60]
    print(f"{indent}<{elem.name}{elem_id}{cls_str}>  {text!r}")
    for child in list(elem.children)[:5]:
        if hasattr(child, "name") and child.name:
            describe(child, depth + 1, max_depth)


with Inspector() as s:
    print(f"Fetching {TARGET_URL} ...\n")
    soup = s.soup(TARGET_URL)

    # ------------------------------------------------------------------
    # 1. All CSS classes and how often they appear
    # ------------------------------------------------------------------
    print("=" * 78)
    print("TOP 30 CSS CLASSES (most frequent = likely card containers)")
    print("=" * 78)
    counter = Counter()
    for tag in soup.find_all(True):
        for cls in tag.get("class", []):
            counter[cls] += 1

    for cls, count in counter.most_common(30):
        print(f"  {count:>4}×  .{cls}")

    # ------------------------------------------------------------------
    # 2. Look for elements repeated with the same class (event cards)
    # ------------------------------------------------------------------
    print()
    print("=" * 78)
    print("REPEATED ELEMENTS (candidates for event cards)")
    print("=" * 78)

    # Find divs/articles/li that appear many times with the same class
    candidates = []
    for tag_name in ("div", "article", "li", "tr"):
        for cls, count in counter.items():
            if count >= 10:  # appears 10+ times → likely a card or row
                elems = soup.find_all(tag_name, class_=cls)
                if len(elems) >= 10:
                    # Check if these elements contain text (not just layout)
                    avg_text = sum(len(e.get_text(strip=True)) for e in elems[:10]) / min(10, len(elems))
                    if avg_text > 50:  # has meaningful content
                        candidates.append((tag_name, cls, len(elems), avg_text))

    candidates.sort(key=lambda x: -x[2])
    for tag_name, cls, count, avg_text in candidates[:15]:
        print(f"  <{tag_name} class='{cls}'>  ×{count}  (avg text: {avg_text:.0f} chars)")

    # ------------------------------------------------------------------
    # 3. Sample structure of the most likely event card
    # ------------------------------------------------------------------
    if candidates:
        top_tag, top_cls = candidates[0][0], candidates[0][1]
        print()
        print("=" * 78)
        print(f"SAMPLE STRUCTURE OF TOP CANDIDATE: <{top_tag} class='{top_cls}'>")
        print("=" * 78)
        first_card = soup.find(top_tag, class_=top_cls)
        if first_card:
            describe(first_card, max_depth=5)

    # ------------------------------------------------------------------
    # 4. Look for <a> tags with event-like hrefs
    # ------------------------------------------------------------------
    print()
    print("=" * 78)
    print("SAMPLE EVENT LINKS (first 10)")
    print("=" * 78)
    for a in soup.find_all("a", href=True)[:200]:
        href = a["href"]
        # Filter for likely event links (contain /expo, /event, /trade-show)
        if any(k in href.lower() for k in ("/expo", "/event", "/trade-show", "/fair")):
            text = a.get_text(strip=True)[:60]
            if text:
                print(f"  {text!r}")
                print(f"    → {href}")
                if sum(1 for _ in [1]) >= 10:
                    break
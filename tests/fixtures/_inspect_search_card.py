"""Inspect the actual structure of a search-result card."""
from bs4 import BeautifulSoup
from scrapers.base_scraper import BaseScraper


URL = "https://exhibitionglobe.com/?s=ahmedabad"


def dump(elem, indent=0, max_depth=6):
    if indent > max_depth:
        return
    pad = "  " * indent
    classes = " ".join(elem.get("class", []))
    eid = f"#{elem.get('id')}" if elem.get("id") else ""
    cls_str = f".{classes.replace(' ', '.')}" if classes else ""
    extra = ""
    for attr in ("href", "src", "datetime"):
        if elem.get(attr):
            extra += f'  {attr}="{str(elem[attr])[:70]}"'
    text = elem.get_text(" ", strip=True)[:60]
    text_str = f"  → {text!r}" if text else ""
    print(f"{pad}<{elem.name}{eid}{cls_str}>{extra}{text_str}")
    for child in elem.children:
        if hasattr(child, "name") and child.name:
            dump(child, indent + 1, max_depth)


with BaseScraper() as s:
    s.BASE_URL = "https://exhibitionglobe.com"
    soup = s.soup(URL)

    print("=" * 78)
    print("ALL ARTICLE TAGS AND THEIR CLASSES")
    print("=" * 78)
    for art in soup.find_all("article"):
        classes = " ".join(art.get("class", []))
        print(f"  <article class='{classes}'>")

    print()
    print("=" * 78)
    print("FULL STRUCTURE OF FIRST ARTICLE")
    print("=" * 78)
    first = soup.find("article")
    if first:
        dump(first, max_depth=6)

    print()
    print("=" * 78)
    print("FIELD EXTRACTION TEST ON FIRST 3 ARTICLES")
    print("=" * 78)
    for i, art in enumerate(soup.find_all("article")[:3], 1):
        print(f"\n--- Article {i} ---")

        # Try many title selectors
        title_candidates = [
            "h1 a", "h2 a", "h3 a", "h4 a",
            ".entry-title a", ".post-title a",
            "a.entry-title-link", "a[rel='bookmark']",
        ]
        for css in title_candidates:
            el = art.select_one(css)
            if el:
                print(f"  ✓ {css:25} → {el.get_text(strip=True)[:60]!r}")
                print(f"     href = {el.get('href')}")
                break
        else:
            # Last resort: any <a> inside a heading
            h = art.find(["h1", "h2", "h3", "h4"])
            if h:
                a = h.find("a")
                if a:
                    print(f"  ✓ <h*><a>            → {a.get_text(strip=True)[:60]!r}")
                    print(f"     href = {a.get('href')}")

        # Date
        for css in ("time", ".posted-on", ".entry-date", ".post-date"):
            el = art.select_one(css)
            if el:
                print(f"  date({css}): {el.get_text(strip=True)!r}  datetime={el.get('datetime')}")

        # Image
        img = art.find("img")
        if img:
            src = img.get("src") or img.get("data-src") or ""
            print(f"  image: {src[:80]}")

        # Categories
        cats = [c.get_text(strip=True) for c in art.select(".cat-links a, .category a")]
        if cats:
            print(f"  cats: {cats}")

        # Excerpt
        excerpt = art.select_one(".entry-summary, .excerpt, .entry-content")
        if excerpt:
            print(f"  excerpt: {excerpt.get_text(strip=True)[:120]!r}")
"""
scrapers/exhibition_globe.py
----------------------------
Scraper for exhibitionglobe.com — searches Ahmedabad & Vadodara expos
across all categories (technical + non-technical).

Pipeline:
    1. For each search query → fetch search page
    2. Extract card links (using card_fields from selectors.yaml)
    3. Dedupe URLs
    4. For each URL → fetch detail page
    5. Filter: must mention Ahmedabad or Vadodara
    6. Skip obvious non-event articles (top 10 lists, news, etc.)
    7. Extract: title, description, dates, venue, city, fees, category
    8. Return list of clean dicts ready for the DB

Usage:
    from scrapers.exhibition_globe import ExhibitionGlobeScraper
    with ExhibitionGlobeScraper() as s:
        records = s.scrape()
"""

from __future__ import annotations

from typing import Any, Optional
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

from config.settings import MAX_PAGES_PER_SITE
from parsers.cleaner import (
    classify,
    clean_text,
    extract_venue,
    matches_target_city,
    parse_date_range,
    parse_fee,
)
from scrapers.base_scraper import BaseScraper, FetchError
from utils.helpers import is_safe_url, site_selectors
from utils.logger import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Non-event title patterns (news, listicles, guides) — skip these
# ---------------------------------------------------------------------------
SKIP_TITLE_PATTERNS = [
    "top 10", "top 20", "best top", "top trade", "list of",
    "guide to", "how to", "why ", "won the ", " wins ",
    "award", "emergency landing", "largest bank",
    "it hubs", "landscape", "opportunities:",
    "mapping ", "global shift", "redefining the",
]


class ExhibitionGlobeScraper(BaseScraper):
    """Scrape all Ahmedabad/Vadodara expos from exhibitionglobe.com."""

    SITE_NAME = "exhibition_globe"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.sel = site_selectors("exhibition_globe")
        self.BASE_URL = self.sel["base_url"]

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def scrape(self, *, max_records: Optional[int] = None) -> list[dict[str, Any]]:
        """Run the full pipeline. Returns DB-ready records."""
        log.info("Starting {} scraper", self.SITE_NAME)

        card_urls = self._collect_card_urls()
        log.info("Collected {} unique card URLs", len(card_urls))

        if not card_urls:
            log.warning("No cards found — check search queries or site structure")
            return []

        card_urls = card_urls[:MAX_PAGES_PER_SITE]

        records: list[dict[str, Any]] = []
        try:
            for i, url in enumerate(card_urls, 1):
                log.debug("Processing [{}/{}] {}", i, len(card_urls), url)
                try:
                    record = self._parse_detail(url)
                except FetchError as e:
                    log.warning("Failed to fetch {}: {}", url, e)
                    continue
                except Exception as e:
                    log.debug("Skipping {} — {}", url, e)
                    continue

                if record:
                    records.append(record)
                    log.info("✅ {} — {}", record["city"], record["name"][:70])
                else:
                    log.debug("⏭️  Skipped: {}", url)

                if max_records and len(records) >= max_records:
                    log.info("Hit max_records={}, stopping", max_records)
                    break
        except KeyboardInterrupt:
            log.warning(
                "⏸️  Interrupted by user — keeping {} records collected so far",
                len(records),
            )

        log.info(
            "Scrape complete: {} records from {} pages ({} filtered out)",
            len(records),
            len(card_urls),
            len(card_urls) - len(records),
        )
        return records

    # ------------------------------------------------------------------ #
    # Step 1 — Collect card URLs
    # ------------------------------------------------------------------ #
    def _collect_card_urls(self) -> list[str]:
        """Run every search query, paginate, dedupe."""
        all_urls: list[str] = []
        seen: set[str] = set()

        queries = self.sel.get("search_queries", ["ahmedabad", "vadodara"])
        max_pages = int(self.sel.get("max_search_pages", 3))
        template = self.sel["search_url_template"]

        card_selector = self.sel["event_card"]
        link_selector = self.sel["card_fields"]["link"].replace("::attr(href)", "")

        for query in queries:
            for page in range(1, max_pages + 1):
                url = self._build_search_url(template, query, page)

                if not is_safe_url(url, self.SITE_NAME):
                    log.debug("Skipping forbidden URL: {}", url)
                    continue

                try:
                    soup = self.soup(url)
                except FetchError as e:
                    log.warning("Search page failed [{} page {}]: {}", query, page, e)
                    break

                cards = soup.select(card_selector)
                if not cards:
                    log.debug("No cards on '{}' page {} — stopping", query, page)
                    break

                new_this_page = 0
                for card in cards:
                    link_el = card.select_one(link_selector)
                    if not link_el:
                        continue
                    href = link_el.get("href")
                    if not href:
                        continue

                    abs_url = urljoin(self.BASE_URL, href)
                    clean = self._canonical_url(abs_url)
                    if clean and clean not in seen:
                        seen.add(clean)
                        all_urls.append(clean)
                        new_this_page += 1

                log.info(
                    "Query '{}' page {} → {} cards, {} new URLs (total: {})",
                    query,
                    page,
                    len(cards),
                    new_this_page,
                    len(all_urls),
                )

        return all_urls

    @staticmethod
    def _build_search_url(template: str, query: str, page: int) -> str:
        """WordPress pagination: &paged=N (only for page > 1)."""
        base = template.format(query=query.replace(" ", "+"))
        if page <= 1:
            return base
        sep = "&" if "?" in base else "?"
        return f"{base}{sep}paged={page}"

    @staticmethod
    def _canonical_url(url: str) -> str:
        """Strip query strings and fragments for dedup."""
        parsed = urlparse(url)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))

    # ------------------------------------------------------------------ #
    # Step 2 — Parse a detail page
    # ------------------------------------------------------------------ #
    def _parse_detail(self, url: str) -> Optional[dict[str, Any]]:
        """
        Fetch a detail page and extract fields.
        Returns a record dict if target-city, else None.
        """
        soup = self.soup(url)

        # -------- Title --------
        title_el = soup.select_one(self.sel["detail_fields"]["title"])
        title = clean_text(title_el.get_text()) if title_el else ""
        if not title:
            log.debug("No <h1> on {}", url)
            return None

        # -------- Skip obvious non-event articles --------
        title_lower = title.lower()
        if any(p in title_lower for p in SKIP_TITLE_PATTERNS):
            log.debug("⏭️  Skipping non-event article: {}", title[:60])
            return None

        # -------- Body text --------
        body_el = soup.select_one(self.sel["detail_fields"]["body_content"])
        if not body_el:
            for fb in self.sel["detail_fields"].get("body_fallback", []):
                body_el = soup.select_one(fb)
                if body_el:
                    break

        body_text = clean_text(body_el.get_text(" ", strip=True)) if body_el else ""

        # -------- Filter: must mention Ahmedabad or Vadodara --------
        combined = f"{title} {body_text}"
        target_city = matches_target_city(combined)
        if not target_city:
            return None

        # -------- Extract fields --------
        start_date, end_date = parse_date_range(body_text)
        venue = extract_venue(body_text)
        fees, currency = parse_fee(body_text)

        # Classify from title + first 300 chars only (not the whole article)
        classify_input = f"{title} {body_text[:300]}"
        category, sub_category = classify(classify_input)

        description = (
            body_text[:500].rsplit(" ", 1)[0] + "…"
            if len(body_text) > 500
            else body_text
        )

        image_url = None
        og_img = soup.find("meta", property="og:image")
        if og_img:
            image_url = og_img.get("content")

        return {
            "source": self.SITE_NAME,
            "source_url": url,
            "name": title,
            "category": category,
            "sub_category": sub_category,
            "description": description,
            "venue": venue,
            "address": None,
            "city": target_city,
            "state": "Gujarat",
            "country": "India",
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "fees": fees,
            "currency": currency,
            "organizer": None,
            "website": url,
            "image_url": image_url,
        }


# ---------------------------------------------------------------------------
# Convenience function for main.py
# ---------------------------------------------------------------------------
def scrape() -> list[dict[str, Any]]:
    """Top-level entry: run the scraper and return records."""
    with ExhibitionGlobeScraper() as s:
        records = s.scrape()
        if records:
            s.save_raw(records, suffix="processed")
    return records


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    records = scrape()
    print(f"\n{'='*70}")
    print(f"FOUND {len(records)} RECORDS")
    print(f"{'='*70}\n")
    for r in records:
        print(f"📌 {r['name'][:70]}")
        print(f"   City     : {r['city']}")
        print(f"   Category : {r['category']} / {r['sub_category']}")
        print(f"   Dates    : {r['start_date']} → {r['end_date']}")
        print(f"   Venue    : {r['venue']}")
        print(f"   Fees     : {r['fees']} {r['currency'] or ''}")
        print(f"   URL      : {r['source_url']}")
        print()
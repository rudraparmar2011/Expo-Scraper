"""
parsers/cleaner.py
------------------
Text cleaning and field-extraction helpers used by all scrapers.

Functions:
    clean_text(s)               -> str
    clean_html(s)               -> str
    parse_fee(text)             -> (amount, currency)
    parse_date_range(text)      -> (start_date, end_date)
    parse_single_date(text)     -> date | None
    extract_venue(text)         -> str | None
    extract_city(text)          -> str | None
    matches_target_city(text)   -> str | None   # Ahmedabad / Vadodara only
    is_target_city(text)        -> bool
    classify(text)              -> (main_category, sub_category)
"""

from __future__ import annotations

import html
import re
from datetime import date
from typing import Optional

from utils.logger import get_logger

log = get_logger(__name__)


# ===========================================================================
# Text cleanup
# ===========================================================================
_WS_RE = re.compile(r"\s+")
_TAG_RE = re.compile(r"<[^>]+>")
_HTML_ENTITIES_RE = re.compile(r"&[a-zA-Z]+;|&#\d+;")


def clean_text(text: Optional[str]) -> str:
    """Collapse whitespace, decode HTML entities, strip control chars."""
    if not text:
        return ""
    text = html.unescape(str(text))
    text = text.replace("\u200b", "").replace("\xa0", " ")
    text = _WS_RE.sub(" ", text)
    return text.strip()


def clean_html(text: Optional[str]) -> str:
    """Strip HTML tags and return clean text."""
    if not text:
        return ""
    text = _TAG_RE.sub(" ", str(text))
    text = _HTML_ENTITIES_RE.sub(" ", text)
    return clean_text(text)


# ===========================================================================
# Target cities (project scope: Ahmedabad & Vadodara only)
# ===========================================================================
TARGET_CITIES: dict[str, str] = {
    "ahmedabad": "Ahmedabad",
    "amdavad": "Ahmedabad",
    "vadodara": "Vadodara",
    "baroda": "Vadodara",
    "sayajigunj": "Vadodara",
}

# Broader list for context (not filtered by default)
_KNOWN_CITIES: dict[str, str] = {
    **TARGET_CITIES,
    "new delhi": "New Delhi", "delhi": "New Delhi",
    "mumbai": "Mumbai", "bombay": "Mumbai",
    "bengaluru": "Bengaluru", "bangalore": "Bengaluru",
    "chennai": "Chennai", "madras": "Chennai",
    "kolkata": "Kolkata", "calcutta": "Kolkata",
    "hyderabad": "Hyderabad", "pune": "Pune",
    "surat": "Surat", "rajkot": "Rajkot",
    "gandhinagar": "Gandhinagar",
    "jaipur": "Jaipur", "lucknow": "Lucknow",
    "noida": "Noida", "gurugram": "Gurugram", "gurgaon": "Gurugram",
    "kochi": "Kochi", "cochin": "Kochi",
    "indore": "Indore", "nagpur": "Nagpur",
    "chandigarh": "Chandigarh", "goa": "Goa",
}


def matches_target_city(text: Optional[str]) -> Optional[str]:
    """
    Return canonical target-city name if `text` mentions Ahmedabad or Vadodara.

    Returns "Ahmedabad", "Vadodara", or None.
    """
    if not text:
        return None
    text_lower = clean_text(text).lower()
    for key in sorted(TARGET_CITIES, key=len, reverse=True):
        if re.search(rf"\b{re.escape(key)}\b", text_lower):
            return TARGET_CITIES[key]
    return None


def is_target_city(text: Optional[str]) -> bool:
    """True if text mentions Ahmedabad or Vadodara."""
    return matches_target_city(text) is not None


def extract_city(text: Optional[str]) -> Optional[str]:
    """Return canonical city name if any known city appears in text."""
    if not text:
        return None
    text_lower = clean_text(text).lower()
    for key in sorted(_KNOWN_CITIES, key=len, reverse=True):
        if re.search(rf"\b{re.escape(key)}\b", text_lower):
            return _KNOWN_CITIES[key]
    return None


# ===========================================================================
# Fees
# ===========================================================================
_FEE_RE = re.compile(
    r"(?:"
    r"(?P<symbol>[₹$€£])\s*(?P<amount1>\d[\d,]*(?:\.\d+)?)"
    r"|"
    r"(?P<currency>INR|USD|EUR|GBP|Rs\.?)\s*(?P<amount2>\d[\d,]*(?:\.\d+)?)"
    r"|"
    r"(?P<amount3>\d[\d,]*(?:\.\d+)?)\s*(?P<currency2>INR|USD|EUR|GBP)"
    r")",
    re.IGNORECASE,
)

_FREE_RE = re.compile(r"\b(free|no fee|free entry|complimentary)\b", re.IGNORECASE)

_SYMBOL_TO_CURRENCY = {
    "₹": "INR", "Rs": "INR", "Rs.": "INR",
    "$": "USD", "€": "EUR", "£": "GBP",
}


def parse_fee(text: Optional[str]) -> tuple[Optional[float], Optional[str]]:
    """
    Extract (amount, currency) from a fee string.

    >>> parse_fee("Entry fee: ₹5,000")
    (5000.0, 'INR')
    >>> parse_fee("Free entry")
    (0.0, None)
    """
    if not text:
        return None, None
    text = clean_text(text)

    if _FREE_RE.search(text):
        return 0.0, None

    m = _FEE_RE.search(text)
    if not m:
        return None, None

    try:
        if m.group("amount1"):
            raw = m.group("amount1").replace(",", "").strip()
            if not raw:
                return None, None
            amount = float(raw)
            currency = _SYMBOL_TO_CURRENCY.get(m.group("symbol"), None)
        elif m.group("amount2"):
            raw = m.group("amount2").replace(",", "").strip()
            if not raw:
                return None, None
            amount = float(raw)
            currency = m.group("currency").upper().replace("RS.", "INR").replace("RS", "INR")
        elif m.group("amount3"):
            raw = m.group("amount3").replace(",", "").strip()
            if not raw:
                return None, None
            amount = float(raw)
            currency = m.group("currency2").upper()
        else:
            return None, None
    except (ValueError, AttributeError):
        return None, None

    return amount, currency

# ===========================================================================
# Dates
# ===========================================================================
_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}

_RANGE_RE = re.compile(
    r"(?P<d1>\d{1,2})\s*[-–—]+\s*(?P<d2>\d{1,2})\s+(?P<mon>\w{3,9})\.?,?\s+(?P<year>\d{4})",
    re.IGNORECASE,
)

_SINGLE_RE = re.compile(
    r"(?P<d>\d{1,2})\s+(?P<mon>\w{3,9})\.?,?\s+(?P<year>\d{4})",
    re.IGNORECASE,
)

_US_RANGE_RE = re.compile(
    r"(?P<mon>\w{3,9})\.?\s+(?P<d1>\d{1,2})\s*[-–—]+\s*(?P<d2>\d{1,2}),?\s+(?P<year>\d{4})",
    re.IGNORECASE,
)


def parse_date_range(text: Optional[str]) -> tuple[Optional[date], Optional[date]]:
    """
    Extract (start, end) from free text.

    >>> parse_date_range("17–19 September 2026")
    (date(2026, 9, 17), date(2026, 9, 19))
    """
    if not text:
        return None, None
    text = clean_text(text)

    m = _RANGE_RE.search(text)
    if m:
        mon = _MONTHS.get(m.group("mon").lower())
        year = int(m.group("year"))
        if mon:
            try:
                start = date(year, mon, int(m.group("d1")))
                end = date(year, mon, int(m.group("d2")))
                if end < start:
                    end = start
                return start, end
            except ValueError:
                pass

    m = _US_RANGE_RE.search(text)
    if m:
        mon = _MONTHS.get(m.group("mon").lower())
        year = int(m.group("year"))
        if mon:
            try:
                start = date(year, mon, int(m.group("d1")))
                end = date(year, mon, int(m.group("d2")))
                if end < start:
                    end = start
                return start, end
            except ValueError:
                pass

    m = _SINGLE_RE.search(text)
    if m:
        mon = _MONTHS.get(m.group("mon").lower())
        year = int(m.group("year"))
        if mon:
            try:
                d = date(year, mon, int(m.group("d")))
                return d, d
            except ValueError:
                pass

    return None, None


def parse_single_date(text: Optional[str]) -> Optional[date]:
    """Return the first date found, or None."""
    start, _ = parse_date_range(text)
    return start


# ===========================================================================
# Venue extraction
# ===========================================================================
_VENUE_RE = re.compile(
    r"(?:at|held at|venue[:\s]+|location[:\s]+)\s+"
    r"(?P<venue>[A-Z][\w\s,\.'&-]{3,80}?)"
    r"(?=[\.\n,]|$|\s+(?:from|on|in|during|will|to|,))",
    re.MULTILINE,
)


def extract_venue(text: Optional[str]) -> Optional[str]:
    """Try to pull a venue name from prose."""
    if not text:
        return None
    m = _VENUE_RE.search(clean_text(text))
    if m:
        venue = m.group("venue").strip(" .,-")
        # Drop overly generic captures
        if len(venue) > 3 and venue.lower() not in {"the", "this", "india"}:
            return venue
    return None


# ===========================================================================
# Category classification
# ===========================================================================
_CATEGORY_MAP: list[tuple[str, str, list[str]]] = [
    # ============ TECHNICAL ============
    ("Technical", "Technology & IT", [
        "tech", "software", "information technology", "artificial intelligence",
        "machine learning", "cloud", "cyber", "data", "semiconductor",
        "electronics", "robotics", "automation", "iot", "blockchain",
        "saas", "developer", "coding", "programming", "5g", "telecom",
        "digital", "startup", "hackathon", "devops", "fintech", "edtech",
    ]),
    ("Technical", "Engineering & Industrial", [
        "industrial", "manufacturing", "machinery", "factory", "welding",
        "plastics", "packaging", "cnc", "3d printing", "mechanical",
        "electrical", "civil engineering", "chemical",
    ]),
    ("Technical", "Healthcare & Pharma", [
        "pharma", "biotech", "diagnostic", "surgical", "medical device",
    ]),
    ("Technical", "Automotive & Transport", [
        "auto expo", "automobile", "electric vehicle", "ev expo",
        "motor show", "logistics",
    ]),
    ("Technical", "Science & Research", [
        "science", "research", "space", "aerospace", "defence", "nuclear",
    ]),

    # ============ NON-TECHNICAL ============
    ("Non-Technical", "Fashion & Lifestyle", [
        "fashion", "textile", "apparel", "garment", "clothing", "lifestyle",
        "jewellery", "jewelry", "beauty", "cosmetic", "wedding", "bridal",
    ]),
    ("Non-Technical", "Food & Agriculture", [
        "food", "beverage", "agriculture", "agri", "dairy", "bakery",
        "restaurant", "hospitality", "culinary", "spice", "organic",
        "farming", "floriculture",
    ]),
    ("Non-Technical", "Education & Career", [
        "education", "university", "college", "career", "job fair",
        "recruitment", "admission", "study abroad", "scholarship",
    ]),
    ("Non-Technical", "Real Estate & Construction", [
        "real estate", "property", "construction", "architecture",
        "infrastructure", "interior", "housing",
    ]),
    ("Non-Technical", "Business & Trade", [
        "business", "trade", "b2b", "conference", "summit", "expo",
        "fair", "commerce", "retail", "franchise",
    ]),
    ("Non-Technical", "Arts & Culture", [
        "art ", "culture", "music", "dance", "theatre", "film", "cinema",
        "photography", "handicraft", "craft", "literature", "book fair",
        "festival", "heritage",
    ]),
    ("Non-Technical", "Health & Wellness", [
        "wellness", "yoga", "fitness", "ayurveda", "spa", "nutrition",
        "mental health",
    ]),
    ("Non-Technical", "Sports & Entertainment", [
        "sport", "tournament", "cricket", "football", "marathon",
        "gaming", "esports",
    ]),
    ("Non-Technical", "Government & Social", [
        "government", "social", "ngo", "csr", "public", "civic",
    ]),
]


def classify(text: Optional[str]) -> tuple[str, Optional[str]]:
    """
    Classify text into (main_category, sub_category).

    Weights the *title* heavily — most events are named after their domain.
    """
    if not text:
        return "Uncategorised", None
    text_lower = clean_text(text).lower()

    # First 200 chars = intro/title — weight this heavily
    header = text_lower[:200]

    # Pass 1: check header first (most accurate)
    for main_cat, sub_cat, keywords in _CATEGORY_MAP:
        for kw in keywords:
            if kw in header:
                return main_cat, sub_cat

    # Pass 2: fall back to full text
    for main_cat, sub_cat, keywords in _CATEGORY_MAP:
        for kw in keywords:
            if kw in text_lower:
                return main_cat, sub_cat

    return "Uncategorised", None

# ===========================================================================
# Self-test
# ===========================================================================
if __name__ == "__main__":
    tests = [
        ("clean_text", clean_text("  Hello   <b>world</b>  &nbsp;  ")),
        ("clean_html", clean_html("<p>SEMICON India 2026</p><br/>")),
        ("parse_fee ₹", parse_fee("Entry fee: ₹5,000")),
        ("parse_fee free", parse_fee("Free entry for all")),
        ("parse_fee USD", parse_fee("Ticket: 50 USD")),
        ("date_range", parse_date_range("set to take place from 17–19 September 2026 at Yashobhoomi")),
        ("date_single", parse_date_range("Held on 15 September 2026")),
        ("date_us", parse_date_range("September 15-18, 2026")),
        ("venue", extract_venue("The event will be held at Yashobhoomi, New Delhi")),
        ("city", extract_city("SEMICON India 2026 in New Delhi")),
        ("classify", classify("SEMICON India 2026 semiconductor event")),
        ("classify2", classify("SUTRAA Indian Fashion Exhibition Nagpur")),
        ("classify3", classify("Agri Food Expo Mumbai")),
        ("target AMD", matches_target_city("Plastindia 2026 at Ahmedabad")),
        ("target BRD", matches_target_city("Vibrant Gujarat in Vadodara")),
        ("not target", matches_target_city("SEMICON India in New Delhi")),
    ]
    for name, result in tests:
        print(f"{name:20}  →  {result}")
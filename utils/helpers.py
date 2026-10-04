"""
utils/helpers.py
----------------
Reusable helper functions used across scrapers, parsers, and the dashboard.

Includes:
    - load_selectors()       : cached YAML selector loader
    - site_selectors(site)   : per-site selector block
    - is_safe_url(url, site) : robots.txt-pattern guard
    - event_hash(record)     : deterministic hash for dedupe/change detection
    - slugify_text(text)     : URL-safe slug
    - parse_int / parse_float: lenient numeric parsers
    - clean_whitespace(text) : squash runs of whitespace
    - truncate(text, n)      : safe truncation
"""

from __future__ import annotations

import hashlib
import re
from functools import lru_cache
from typing import Any, Optional

import yaml

from config.settings import CONFIG_DIR
from utils.logger import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Selectors (YAML)
# ---------------------------------------------------------------------------
_SELECTORS_PATH = CONFIG_DIR / "selectors.yaml"


@lru_cache(maxsize=1)
def load_selectors() -> dict[str, Any]:
    """
    Load and cache `config/selectors.yaml`.

    Returns
    -------
    dict
        Full parsed YAML.
    """
    if not _SELECTORS_PATH.exists():
        raise FileNotFoundError(f"Selectors file not found: {_SELECTORS_PATH}")

    with _SELECTORS_PATH.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    log.debug("Loaded selectors for %d sites", len(data))
    return data


def site_selectors(site: str) -> dict[str, Any]:
    """
    Return the selector block for a specific site key.

    Parameters
    ----------
    site : str
        Top-level YAML key, e.g. "ten_times".

    Raises
    ------
    KeyError
        If `site` is not defined in selectors.yaml.
    """
    data = load_selectors()
    if site not in data:
        available = ", ".join(k for k in data if not k.startswith("_"))
        raise KeyError(
            f"No selectors for site '{site}'. Available: {available}"
        )
    return data[site]


def reload_selectors() -> None:
    """Clear the cache — call after editing selectors.yaml at runtime."""
    load_selectors.cache_clear()


# ---------------------------------------------------------------------------
# URL safety
# ---------------------------------------------------------------------------
def is_safe_url(url: str, site: str) -> bool:
    """
    Return True if `url` is NOT matched by the site's `forbidden_patterns`
    in selectors.yaml. Extra guard on top of robots.txt.
    """
    try:
        section = site_selectors(site)
    except KeyError:
        return True

    patterns = section.get("forbidden_patterns", [])
    for pattern in patterns:
        if pattern in url:
            log.debug("URL blocked by pattern '%s': %s", pattern, url)
            return False
    return True


# ---------------------------------------------------------------------------
# Hashing (for dedupe / change detection)
# ---------------------------------------------------------------------------
def event_hash(record: dict[str, Any]) -> str:
    """
    Deterministic hash from the (name, venue, start_date) triple.

    Used to skip unchanged events on re-scrapes.
    """
    key = "|".join(
        str(record.get(k, "") or "").strip().lower()
        for k in ("name", "venue", "start_date")
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]


# ---------------------------------------------------------------------------
# Text utilities
# ---------------------------------------------------------------------------
_WS_RE = re.compile(r"\s+")
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def clean_whitespace(text: Optional[str]) -> str:
    """Collapse all whitespace runs into a single space and strip edges."""
    if not text:
        return ""
    return _WS_RE.sub(" ", text).strip()


def slugify_text(text: Optional[str]) -> str:
    """Convert text to a URL-safe lowercase slug."""
    if not text:
        return ""
    return _SLUG_RE.sub("-", text.lower()).strip("-")


def truncate(text: Optional[str], max_len: int = 500, suffix: str = "…") -> str:
    """Truncate text to max_len characters, appending suffix if cut."""
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[: max_len - len(suffix)].rstrip() + suffix


# ---------------------------------------------------------------------------
# Lenient numeric parsing
# ---------------------------------------------------------------------------
_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


def parse_int(value: Any) -> Optional[int]:
    """Extract first integer from a string. Returns None if none found."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    match = _NUM_RE.search(str(value).replace(",", ""))
    if not match:
        return None
    try:
        return int(float(match.group()))
    except ValueError:
        return None


def parse_float(value: Any) -> Optional[float]:
    """Extract first float from a string. Returns None if none found."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = _NUM_RE.search(str(value).replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Small dict helpers
# ---------------------------------------------------------------------------
def pick(d: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    """Return a new dict containing only the given keys (if present)."""
    return {k: d[k] for k in keys if k in d}


def drop_empty(d: dict[str, Any]) -> dict[str, Any]:
    """Return a new dict without None / empty-string values."""
    return {k: v for k, v in d.items() if v not in (None, "", [], {})}


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("--- load_selectors() ---")
    sel = load_selectors()
    print("sites:", [k for k in sel if not k.startswith("_")])

    print("\n--- site_selectors('ten_times') ---")
    tt = site_selectors("ten_times")
    print("event_row:", tt.get("event_row"))

    print("\n--- is_safe_url() ---")
    print(is_safe_url("https://10times.com/e/abc", "ten_times"))          # True
    print(is_safe_url("https://10times.com/search?q=tech", "ten_times"))  # False
    print(is_safe_url("https://10times.com/ajax?for=scroll", "ten_times"))# False

    print("\n--- event_hash() ---")
    h = event_hash({"name": "Demo Expo", "venue": "Delhi", "start_date": "2026-10-15"})
    print("hash:", h)

    print("\n--- text utils ---")
    print(repr(clean_whitespace("  hello   world  ")))
    print(slugify_text("India Mobile Congress 2026!"))
    print(truncate("a" * 600, 20))

    print("\n--- numeric parsing ---")
    print(parse_int("Interested 1,234 following"))   # 1234
    print(parse_float("₹ 5,000.50"))                 # 5000.5
    print(parse_int("no numbers here"))              # None
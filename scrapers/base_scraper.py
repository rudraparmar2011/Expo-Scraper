"""
scrapers/base_scraper.py
------------------------
Base class for all site scrapers.

Provides:
    - requests.Session with realistic browser-like default headers
    - Exponential backoff retries (via tenacity)
    - Rate limiting (REQUEST_DELAY between requests)
    - robots.txt compliance check (opt-out via RESPECT_ROBOTS_TXT=false)
    - Optional Selenium fallback for JS-rendered / bot-protected pages
    - Automatic Brotli-safe Accept-Encoding negotiation

Every concrete scraper should subclass `BaseScraper` and implement:
    - SITE_NAME: str
    - BASE_URL: str
    - scrape() -> list[dict]
"""

from __future__ import annotations

import json as _json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config.settings import (
    BACKOFF_FACTOR,
    MAX_RETRIES,
    RAW_DIR,
    REQUEST_DELAY,
    REQUEST_TIMEOUT,
    RESPECT_ROBOTS_TXT,
    USER_AGENT,
)
from utils.logger import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Detect whether Brotli decompression is available.
# If not, we must NOT advertise "br" in Accept-Encoding — otherwise the server
# sends Brotli and requests gives us raw compressed bytes (garbled text).
# ---------------------------------------------------------------------------
def _brotli_available() -> bool:
    try:
        import brotli  # noqa: F401
        return True
    except ImportError:
        try:
            import brotlicffi  # noqa: F401
            return True
        except ImportError:
            return False


_BROTLI_OK: bool = _brotli_available()
_ACCEPT_ENCODING: str = "gzip, deflate, br" if _BROTLI_OK else "gzip, deflate"


# ---------------------------------------------------------------------------
# Realistic browser headers
# ---------------------------------------------------------------------------
DEFAULT_BROWSER_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/127.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8,"
        "application/signed-exchange;v=b3;q=0.7"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": _ACCEPT_ENCODING,
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Ch-Ua": '"Chromium";v="127", "Not)A;Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "Connection": "keep-alive",
    "DNT": "1",
}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class ScraperError(Exception):
    """Base exception for scraper-level failures."""


class RobotsDisallowedError(ScraperError):
    """Raised when robots.txt forbids a URL the scraper tried to fetch."""


class FetchError(ScraperError):
    """Raised when a page could not be fetched after retries."""


# ---------------------------------------------------------------------------
# Base scraper
# ---------------------------------------------------------------------------
class BaseScraper:
    """
    Base class every site scraper inherits from.

    Subclasses SHOULD override:
        SITE_NAME : short identifier used in logs, DB, and filenames
        BASE_URL  : root URL used for robots.txt and relative links

    Subclasses MUST implement:
        scrape() -> list[dict]
    """

    SITE_NAME: str = "base"
    BASE_URL: str = ""

    def __init__(
        self,
        *,
        request_delay: Optional[float] = None,
        timeout: Optional[int] = None,
        user_agent: Optional[str] = None,
        extra_headers: Optional[dict[str, str]] = None,
    ) -> None:
        self.request_delay = request_delay if request_delay is not None else REQUEST_DELAY
        self.timeout = timeout if timeout is not None else REQUEST_TIMEOUT
        self.user_agent = user_agent or USER_AGENT

        self.session = requests.Session()

        headers = dict(DEFAULT_BROWSER_HEADERS)
        headers["User-Agent"] = self.user_agent
        if extra_headers:
            headers.update(extra_headers)
        self.session.headers.update(headers)

        self._primed: bool = False
        self._last_request_at: float = 0.0
        self._robots: Optional[RobotFileParser] = None

        log.debug(
            "Initialised {} (delay={:.2f}s, timeout={}s, brotli={}, UA={})",
            self.__class__.__name__,
            self.request_delay,
            self.timeout,
            _BROTLI_OK,
            self.user_agent[:50],
        )

    # ------------------------------------------------------------------ #
    # robots.txt
    # ------------------------------------------------------------------ #
    def _load_robots(self) -> Optional[RobotFileParser]:
        if self._robots is not None:
            return self._robots
        if not self.BASE_URL:
            return None

        robots_url = urljoin(self.BASE_URL, "/robots.txt")
        rp = RobotFileParser()
        rp.set_url(robots_url)

        try:
            response = self.session.get(robots_url, timeout=self.timeout)
            if response.status_code == 200:
                rp.parse(response.text.splitlines())
                log.debug("Loaded robots.txt from {}", robots_url)
            else:
                rp.parse([])
                log.debug(
                    "robots.txt not found at {} (status={}) — allowing all",
                    robots_url,
                    response.status_code,
                )
        except requests.RequestException as exc:
            log.warning("Could not fetch robots.txt ({}) — allowing all", exc)
            rp.parse([])

        self._robots = rp
        return rp

    def can_fetch(self, url: str) -> bool:
        if not RESPECT_ROBOTS_TXT:
            return True
        rp = self._load_robots()
        if rp is None:
            return True
        allowed = rp.can_fetch(self.user_agent, url)
        if not allowed:
            log.warning("robots.txt DISALLOWS: {}", url)
        return allowed

    # ------------------------------------------------------------------ #
    # Rate limiting
    # ------------------------------------------------------------------ #
    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        remaining = self.request_delay - elapsed
        if remaining > 0:
            time.sleep(remaining)

    # ------------------------------------------------------------------ #
    # Session priming
    # ------------------------------------------------------------------ #
    def prime_session(self) -> None:
        if self._primed or not self.BASE_URL:
            return
        try:
            self.session.get(self.BASE_URL, timeout=self.timeout)
            self._primed = True
            log.debug("Primed session at {}", self.BASE_URL)
        except requests.RequestException as exc:
            log.debug("Could not prime session: {}", exc)

    # ------------------------------------------------------------------ #
    # HTTP fetching
    # ------------------------------------------------------------------ #
    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=BACKOFF_FACTOR, min=1, max=30),
        retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout)),
        reraise=True,
    )
    def _raw_get(self, url: str, **kwargs: Any) -> requests.Response:
        self._throttle()
        self._last_request_at = time.monotonic()
        log.debug("GET {}", url)

        headers = kwargs.pop("headers", {}) or {}
        if urlparse(url).netloc and self.BASE_URL:
            base_netloc = urlparse(self.BASE_URL).netloc
            if urlparse(url).netloc == base_netloc:
                headers.setdefault("Referer", self.BASE_URL)

        response = self.session.get(url, timeout=self.timeout, headers=headers, **kwargs)
        response.raise_for_status()
        return response

    def fetch(
        self,
        url: str,
        *,
        allow_robots_bypass: bool = False,
        **kwargs: Any,
    ) -> str:
        if not allow_robots_bypass and not self.can_fetch(url):
            raise RobotsDisallowedError(f"robots.txt disallows: {url}")

        try:
            response = self._raw_get(url, **kwargs)
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "?"
            raise FetchError(f"HTTP {status} for {url}") from exc
        except requests.RequestException as exc:
            raise FetchError(f"Failed to fetch {url}: {exc}") from exc

        # requests sets .text using guessed encoding; force utf-8 if empty
        if not response.encoding:
            response.encoding = "utf-8"

        # Sanity check: if the first bytes look like garbage (null/high-unicode),
        # the server probably sent Brotli while we didn't advertise support.
        text = response.text
        if text and _looks_like_garbage(text):
            log.warning(
                "Suspicious response from {} — first bytes: {!r}. "
                "Try: pip install brotli",
                url,
                text[:40],
            )
        return text

    def soup(self, url: str, *, parser: str = "lxml", **kwargs: Any) -> BeautifulSoup:
        html = self.fetch(url, **kwargs)
        return BeautifulSoup(html, parser)

    def fetch_json(self, url: str, **kwargs: Any) -> Any:
        if not self.can_fetch(url):
            raise RobotsDisallowedError(f"robots.txt disallows: {url}")
        response = self._raw_get(url, **kwargs)
        try:
            return response.json()
        except ValueError as exc:
            raise FetchError(f"Invalid JSON from {url}: {exc}") from exc

    # ------------------------------------------------------------------ #
    # Selenium fallback
    # ------------------------------------------------------------------ #
    def fetch_dynamic(
        self,
        url: str,
        *,
        wait_seconds: float = 5.0,
        headless: bool = True,
        allow_robots_bypass: bool = False,
        scroll: bool = False,
    ) -> str:
        if not allow_robots_bypass and not self.can_fetch(url):
            raise RobotsDisallowedError(f"robots.txt disallows: {url}")

        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
        except ImportError as exc:  # pragma: no cover
            raise ScraperError(
                "Selenium not installed. Run: pip install selenium webdriver-manager"
            ) from exc

        self._throttle()

        options = Options()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument(f"--user-agent={self.user_agent}")
        options.add_argument("--lang=en-US,en")

        driver = None
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)

            driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
            )

            driver.set_page_load_timeout(self.timeout)
            driver.get(url)
            time.sleep(wait_seconds)

            if scroll:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.5)

            html = driver.page_source
        finally:
            if driver is not None:
                try:
                    driver.quit()
                except Exception:  # pragma: no cover
                    pass
            self._last_request_at = time.monotonic()

        log.debug("Rendered {} via Selenium ({} bytes)", url, len(html))
        return html

    # ------------------------------------------------------------------ #
    # Utilities
    # ------------------------------------------------------------------ #
    @staticmethod
    def absolute_url(base: str, link: str) -> str:
        if not link:
            return ""
        return urljoin(base, link.strip())

    @staticmethod
    def slug_from_url(url: str) -> str:
        path = urlparse(url).path.strip("/").replace("/", "_")
        return path or "index"

    def save_raw(
        self,
        data: Any,
        *,
        suffix: str = "",
        subdir: Optional[str] = None,
    ) -> Path:
        target_dir = RAW_DIR / (subdir or self.SITE_NAME)
        target_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        parts = [self.SITE_NAME]
        if suffix:
            parts.append(suffix)
        parts.append(timestamp)
        filename = "_".join(parts) + ".json"

        path = target_dir / filename
        with path.open("w", encoding="utf-8") as fh:
            _json.dump(data, fh, ensure_ascii=False, indent=2, default=str)

        size = len(data) if hasattr(data, "__len__") else 1
        log.info("Saved raw dump -> {} ({} records)", path, size)
        return path

    # ------------------------------------------------------------------ #
    # Contract
    # ------------------------------------------------------------------ #
    def scrape(self) -> list[dict[str, Any]]:
        raise NotImplementedError("Subclasses must implement scrape()")

    # ------------------------------------------------------------------ #
    # Context manager
    # ------------------------------------------------------------------ #
    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "BaseScraper":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


# ---------------------------------------------------------------------------
# Garbage detector (Brotli decompression sanity check)
# ---------------------------------------------------------------------------
def _looks_like_garbage(text: str) -> bool:
    """
    True if `text` looks like binary or uncompressed bytes rather than HTML.
    """
    if not text:
        return False
    sample = text[:200]
    # HTML should almost always start with "<" after any whitespace/BOM
    stripped = sample.lstrip("\ufeff \t\r\n")
    if stripped.startswith("<"):
        return False
    # Count replacement chars and control chars
    bad = sum(1 for ch in sample if ch == "\ufffd" or (ord(ch) < 9))
    return bad > 20


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Brotli available:", _BROTLI_OK)
    print("Accept-Encoding :", _ACCEPT_ENCODING)

    class DemoScraper(BaseScraper):
        SITE_NAME = "demo"
        BASE_URL = "https://example.com"

        def scrape(self) -> list[dict[str, Any]]:
            soup = self.soup(self.BASE_URL)
            title = soup.title.get_text(strip=True) if soup.title else ""
            return [{"source": self.SITE_NAME, "url": self.BASE_URL, "title": title}]

    with DemoScraper() as scraper:
        print("robots.txt allows example.com? ", scraper.can_fetch("https://example.com"))
        records = scraper.scrape()
        print("Scraped:", records)
        path = scraper.save_raw(records)
        print("Saved to:", path)
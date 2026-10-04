"""
config/settings.py
------------------
Central configuration module for the Expo Scraper project.

Loads environment variables from `.env` (via python-dotenv) and exposes
project-wide constants such as paths, network settings, and DB URL.

Never hardcode secrets here — read them from the environment.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load environment variables from .env (if present)
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_FILE, override=False)


# ---------------------------------------------------------------------------
# Project directories
# ---------------------------------------------------------------------------
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
LOG_DIR = BASE_DIR / "logs"
CONFIG_DIR = BASE_DIR / "config"
ASSETS_DIR = BASE_DIR / "dashboard" / "assets"

# Ensure runtime directories exist
for _dir in (DATA_DIR, RAW_DIR, PROCESSED_DIR, LOG_DIR):
    _dir.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Networking / scraping behaviour
# ---------------------------------------------------------------------------
USER_AGENT: str = os.getenv(
    "USER_AGENT",
    "ExpoScraperBot/1.0 (+https://github.com/yourname/expo-scraper)",
)

REQUEST_DELAY: float = float(os.getenv("REQUEST_DELAY", "1.5"))   # seconds between requests
REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "20"))    # seconds
MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
BACKOFF_FACTOR: float = float(os.getenv("BACKOFF_FACTOR", "2.0"))  # exponential backoff
MAX_PAGES_PER_SITE: int = int(os.getenv("MAX_PAGES_PER_SITE", "500"))

# Respect robots.txt before scraping (recommended: keep True)
RESPECT_ROBOTS_TXT: bool = os.getenv("RESPECT_ROBOTS_TXT", "true").lower() == "true"


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# NOTE: We resolve to an ABSOLUTE path so the DB is always found regardless
# of the current working directory (fixes empty-dashboard bug when Streamlit
# is launched from a different folder).
_DB_FILE = (DATA_DIR / "expo.db").resolve()
DB_URL: str = os.getenv("DB_URL", f"sqlite:///{_DB_FILE}")
SQL_ECHO: bool = os.getenv("SQL_ECHO", "false").lower() == "true"


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_ROTATION: str = os.getenv("LOG_ROTATION", "10 MB")
LOG_RETENTION: str = os.getenv("LOG_RETENTION", "7 days")
LOG_FORMAT: str = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)


# ---------------------------------------------------------------------------
# API keys (optional — only used by sources that support APIs)
# ---------------------------------------------------------------------------
EVENTBRITE_API_KEY: str | None = os.getenv("EVENTBRITE_API_KEY")
APIFY_TOKEN: str | None = os.getenv("APIFY_TOKEN")


# ---------------------------------------------------------------------------
# Supported scrapers registry (used by main.py & scheduler/run_all.py)
# ---------------------------------------------------------------------------
SUPPORTED_SITES: tuple[str, ...] = (
    "exhibition_globe",
    "10times",
    "expolume",
    "mera_events",
    "sumvaad",
    "eventbrite",
)


# ---------------------------------------------------------------------------
# Target scope (project focuses ONLY on these cities)
# ---------------------------------------------------------------------------
TARGET_CITIES: tuple[str, ...] = ("Ahmedabad", "Vadodara")
TARGET_STATE: str = "Gujarat"
TARGET_COUNTRY: str = "India"


# ---------------------------------------------------------------------------
# Sanity check (helps catch config mistakes early)
# ---------------------------------------------------------------------------
def _validate() -> None:
    if REQUEST_DELAY < 0.5:
        raise ValueError(
            f"REQUEST_DELAY={REQUEST_DELAY}s is too aggressive. "
            "Use at least 0.5s, preferably >=1.0s, to avoid bans."
        )
    if MAX_RETRIES < 0:
        raise ValueError("MAX_RETRIES must be >= 0")


_validate()


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("BASE_DIR        :", BASE_DIR)
    print("RAW_DIR         :", RAW_DIR)
    print("PROCESSED_DIR   :", PROCESSED_DIR)
    print("LOG_DIR         :", LOG_DIR)
    print("DB_URL          :", DB_URL)
    print("DB file exists  :", _DB_FILE.exists())
    print("USER_AGENT      :", USER_AGENT)
    print("REQUEST_DELAY   :", REQUEST_DELAY)
    print("MAX_RETRIES     :", MAX_RETRIES)
    print("LOG_LEVEL       :", LOG_LEVEL)
    print("SUPPORTED_SITES :", SUPPORTED_SITES)
    print("TARGET_CITIES   :", TARGET_CITIES)
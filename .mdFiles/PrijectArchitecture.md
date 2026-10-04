# 🏗️ Expo Scraper & Dashboard — Project Architecture

> A Python-based web scraping pipeline + interactive dashboard that aggregates
> technical and non-technical expo / trade-show data (name, venue, address,
> description, fees, dates, organizer, etc.) from multiple public sources.

**Version:** 1.0
**Status:** Planning / Early Development
**Last Updated:** 2026

---

## 📑 Table of Contents

1. [Project Overview](#1-project-overview)
2. [Goals & Non-Goals](#2-goals--non-goals)
3. [Tech Stack](#3-tech-stack)
4. [High-Level Architecture](#4-high-level-architecture)
5. [Folder Structure](#5-folder-structure)
6. [Module Responsibilities](#6-module-responsibilities)
7. [Data Model](#7-data-model)
8. [Data Flow](#8-data-flow)
9. [Configuration](#9-configuration)
10. [Python Packages / Dependencies](#10-python-packages--dependencies)
11. [Dashboard Architecture](#11-dashboard-architecture)
12. [Scheduling & Automation](#12-scheduling--automation)
13. [Logging & Error Handling](#13-logging--error-handling)
14. [Testing Strategy](#14-testing-strategy)
15. [Security, Legal & Ethical Considerations](#15-security-legal--ethical-considerations)
16. [Deployment](#16-deployment)
17. [Future Roadmap](#17-future-roadmap)

---

## 1. Project Overview

This project **scrapes expo / trade-show listings** from multiple websites and
**consolidates them into a single database** which is then served through an
interactive **Streamlit dashboard** for exploration, filtering, and export.

It supports both **technical expos** (IT, AI, electronics, biotech, etc.) and
**non-technical expos** (food, fashion, agriculture, real estate, etc.).

**Target data fields per expo:**

| Field | Example |
|---|---|
| Name | India Mobile Congress 2026 |
| Category | Technical / Non-Technical |
| Sub-category | Telecom, AI, Fashion, Food |
| Description | Short summary of the event |
| Venue | Pragati Maidan |
| Address | Mathura Road, New Delhi, 110001 |
| City / State / Country | New Delhi / Delhi / India |
| Start Date | 2026-10-15 |
| End Date | 2026-10-18 |
| Entry Fees | ₹500 / Free / N/A |
| Organizer | COAI |
| Website / Source URL | https://… |
| Source Website | 10times.com |

---

## 2. Goals & Non-Goals

### ✅ Goals
- Scrape structured expo data from ≥ 3 different sources.
- Normalize data into a unified schema.
- Store in a queryable database (SQLite for dev → PostgreSQL for prod).
- Provide a clean, filterable dashboard (Streamlit).
- Be modular: adding a new website = 1 new file in `scrapers/`.
- Respect `robots.txt`, rate limits, and ToS.

### ❌ Non-Goals (v1)
- No user authentication / multi-tenant support.
- No real-time scraping (scheduled daily batch is enough).
- No mobile app.
- No scraping of paid / gated content.

---

## 3. Tech Stack

| Layer | Technology | Why |
|---|---|---|
| **Language** | Python 3.10+ | Ecosystem for scraping + data |
| **HTTP** | `requests`, `httpx` | Simple, fast sync/async HTTP |
| **HTML Parsing** | `BeautifulSoup4`, `lxml` | Fast, forgiving HTML parsing |
| **Dynamic Sites** | `Selenium` + `webdriver-manager`, `Playwright` | For JS-rendered pages |
| **Data Handling** | `pandas`, `numpy` | Cleaning, transformation |
| **DB (dev)** | `SQLite` (via `sqlite3`) | Zero-config, file-based |
| **DB (prod)** | `PostgreSQL` + `SQLAlchemy` | Scale, concurrency |
| **ORM** | `SQLAlchemy 2.x` | DB-agnostic models |
| **Validation** | `pydantic` | Schema enforcement on scraped data |
| **Config** | `python-dotenv`, `PyYAML` | Secrets + selectors |
| **Logging** | `logging` (stdlib) + `loguru` | Structured logs |
| **Dashboard** | `Streamlit` + `Plotly` | Fast, Python-only UI |
| **Scheduling** | `APScheduler` / `cron` / Task Scheduler | Automation |
| **Testing** | `pytest`, `pytest-mock`, `responses` | Unit + integration |
| **Linting** | `ruff`, `black`, `mypy` | Code quality |
| **Version Control** | Git + GitHub | Collaboration |
| **Containerization** | Docker, docker-compose | Reproducible envs |

---

## 4. High-Level Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                        SCHEDULER (cron / APScheduler)              │
│                    runs daily at 02:00 IST                         │
└──────────────────────────┬─────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────────┐
│                        SCRAPER LAYER                               │
│                                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ 10times.py   │  │ Eventbrite.py│  │ ExhibitGlobe │  ... more    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │                 │                 │                      │
│         └────────┬────────┴────────┬────────┘                      │
│                  ▼                 ▼                               │
│         ┌──────────────────────────────────┐                       │
│         │      base_scraper.py             │                       │
│         │  (session, retries, headers,     │                       │
│         │   rate-limit, robots.txt check)  │                       │
│         └──────────────────────────────────┘                       │
└──────────────────────────┬─────────────────────────────────────────┘
                           │  raw HTML / JSON
                           ▼
┌────────────────────────────────────────────────────────────────────┐
│                        PARSER LAYER                                │
│   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐           │
│   │  cleaner.py  │──▶│ normalizer.py│──▶│  pydantic    │           │
│   │  (text, fee, │   │  (city, cat, │   │  validation  │           │
│   │   date)      │   │   country)   │   │              │           │
│   └──────────────┘   └──────────────┘   └──────┬───────┘           │
└───────────────────────────────────────────────┬┴───────────────────┘
                                                │ clean records
                                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                        STORAGE LAYER                               │
│                                                                    │
│   data/raw/         → raw JSON dumps (audit trail)                 │
│   data/processed/   → clean CSV / Parquet                          │
│   data/expo.db      → SQLite (dev)                                 │
│   PostgreSQL        → prod (via SQLAlchemy)                        │
└──────────────────────────┬─────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────────┐
│                        DASHBOARD LAYER                             │
│                                                                    │
│   Streamlit (app.py + pages/)                                      │
│   ├── Overview (metrics, charts)                                   │
│   ├── Expo List (filters, search, download)                        │
│   └── Expo Detail (single event view)                              │
└────────────────────────────────────────────────────────────────────┘
```

---

## 5. Folder Structure

```
expo-scraper/
│
├── scrapers/                     # One file per source website
│   ├── __init__.py
│   ├── base_scraper.py           # Shared HTTP/session/retry logic
│   ├── ten_times.py
│   ├── eventbrite.py
│   ├── exhibition_globe.py
│   ├── expolume.py
│   ├── mera_events.py
│   └── sumvaad.py
│
├── parsers/                      # Cleaning & normalization
│   ├── __init__.py
│   ├── cleaner.py                # Text/fee/date cleanup
│   └── normalizer.py             # City / category / country normalization
│
├── data/                         # All data storage
│   ├── raw/                      # Raw JSON dumps per source
│   ├── processed/                # Clean CSV / Parquet
│   └── expo.db                   # SQLite database (dev)
│
├── dashboard/                    # Streamlit app
│   ├── app.py
│   ├── pages/
│   │   ├── 1_Overview.py
│   │   ├── 2_Expo_List.py
│   │   └── 3_Expo_Detail.py
│   └── assets/
│       └── style.css
│
├── config/                       # Configuration
│   ├── settings.py               # Paths, delays, env loading
│   └── selectors.yaml            # CSS/XPath selectors per site
│
├── utils/                        # Reusable helpers
│   ├── __init__.py
│   ├── logger.py
│   ├── database.py               # SQLAlchemy session / CRUD
│   └── helpers.py
│
├── scheduler/                    # Automation
│   └── run_all.py
│
├── tests/                        # pytest
│   ├── test_scrapers.py
│   ├── test_parsers.py
│   └── test_database.py
│
├── notebooks/                    # Experimentation (Jupyter)
│   └── explore_10times.ipynb
│
├── logs/                         # Auto-generated log files
│
├── .env                          # Secrets (NEVER commit)
├── .gitignore
├── requirements.txt
├── PROJECT_ARCHITECTURE.md       # ← this file
├── README.md
├── main.py                       # CLI entry point
└── run_dashboard.sh              # Helper to launch Streamlit
```

---

## 6. Module Responsibilities

### `scrapers/`
- **`base_scraper.py`** — Base class with:
  - `requests.Session` with custom `User-Agent`
  - Retry logic (exponential backoff)
  - Rate limiting (`REQUEST_DELAY`)
  - `robots.txt` compliance check
  - HTML fetch + optional Selenium fallback
- **`<site>.py`** — Each module exposes a `scrape() -> list[dict]` function
  that returns normalized dicts. Uses selectors from `config/selectors.yaml`.

### `parsers/`
- **`cleaner.py`** — functions like `clean_fee("₹5,000/-") → 5000`,
  `parse_date("15–18 Oct 2026") → (datetime, datetime)`.
- **`normalizer.py`** — canonicalize city/state/category using lookup maps
  (e.g. `"Bombay"` → `"Mumbai"`).

### `utils/`
- **`database.py`** — SQLAlchemy engine, `Session`, `save_expos()`,
  `get_expos(filters)` helpers.
- **`logger.py`** — `loguru` or stdlib logging with rotating file handler.
- **`helpers.py`** — misc (slugify, dedupe, hash for change detection).

### `config/`
- **`settings.py`** — loads `.env`, defines paths & constants.
- **`selectors.yaml`** — per-site CSS selectors, so HTML changes don't
  require Python edits.

### `dashboard/`
- **`app.py`** — main entry, landing page, KPI cards.
- **`pages/`** — Streamlit's multi-page convention.
- **`assets/`** — custom CSS / logos.

### `scheduler/`
- **`run_all.py`** — iterates over all scrapers, saves to DB, logs summary.

### `main.py`
- CLI: `python main.py --site 10times --output db`

---

## 7. Data Model

### 7.1 SQLite / PostgreSQL Schema

```sql
CREATE TABLE expos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT NOT NULL,          -- "10times.com"
    source_url      TEXT UNIQUE NOT NULL,   -- canonical event URL
    name            TEXT NOT NULL,
    category        TEXT,                   -- "Technical" / "Non-Technical"
    sub_category    TEXT,                   -- "AI", "Fashion", ...
    description     TEXT,
    venue           TEXT,
    address         TEXT,
    city            TEXT,
    state           TEXT,
    country         TEXT,
    start_date      DATE,
    end_date        DATE,
    fees            REAL,                   -- NULL if free/unknown
    currency        TEXT,                   -- "INR", "USD"
    organizer       TEXT,
    contact_email   TEXT,
    contact_phone   TEXT,
    website         TEXT,
    scraped_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_expos_city       ON expos(city);
CREATE INDEX idx_expos_category   ON expos(category);
CREATE INDEX idx_expos_start_date ON expos(start_date);
CREATE INDEX idx_expos_source     ON expos(source);
```

### 7.2 Pydantic Model

```python
from pydantic import BaseModel, HttpUrl
from datetime import date
from typing import Optional

class Expo(BaseModel):
    source: str
    source_url: HttpUrl
    name: str
    category: Optional[str] = None
    sub_category: Optional[str] = None
    description: Optional[str] = None
    venue: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    fees: Optional[float] = None
    currency: Optional[str] = None
    organizer: Optional[str] = None
    website: Optional[str] = None
```

---

## 8. Data Flow

```
[1] Scheduler triggers run_all.py
        │
        ▼
[2] For each scraper module:
        - fetch listing pages (requests / Selenium)
        - parse HTML via selectors.yaml
        - build list of raw dicts
        - dump to data/raw/<source>_<date>.json
        │
        ▼
[3] Parser pipeline:
        - cleaner.py   → trim, fee/date parsing
        - normalizer.py → canonical cities/categories
        - pydantic validation
        │
        ▼
[4] Upsert into database (SQLite / Postgres)
        - dedupe on source_url
        - update updated_at on conflict
        │
        ▼
[5] Export snapshot to data/processed/expos_<date>.csv
        │
        ▼
[6] Dashboard reads DB → user filters/searches
```

---

## 9. Configuration

### `.env`
```env
# API Keys
EVENTBRITE_API_KEY=xxxxxxxxxxxx
APIFY_TOKEN=xxxxxxxxxxxx

# Scraper behaviour
REQUEST_DELAY=1.5
MAX_RETRIES=3
USER_AGENT=ExpoScraperBot/1.0 (+contact@yourdomain.com)

# Database
DB_URL=sqlite:///data/expo.db
# DB_URL=postgresql://user:pass@localhost:5432/expo_db

# Logging
LOG_LEVEL=INFO
```

### `config/settings.py`
```python
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR        = Path(__file__).resolve().parent.parent
RAW_DIR         = BASE_DIR / "data" / "raw"
PROCESSED_DIR   = BASE_DIR / "data" / "processed"
LOG_DIR         = BASE_DIR / "logs"

USER_AGENT      = os.getenv("USER_AGENT", "ExpoScraperBot/1.0")
REQUEST_DELAY   = float(os.getenv("REQUEST_DELAY", 1.5))
MAX_RETRIES     = int(os.getenv("MAX_RETRIES", 3))
DB_URL          = os.getenv("DB_URL", f"sqlite:///{BASE_DIR}/data/expo.db")
LOG_LEVEL       = os.getenv("LOG_LEVEL", "INFO")
```

### `config/selectors.yaml`
```yaml
ten_times:
  listing_url: "https://10times.com/trade-shows-in-india"
  event_card:  ".event-card"
  name:        ".event-name"
  venue:       ".venue"
  date:        ".event-date"
  link:        "a.event-link::attr(href)"

exhibition_globe:
  listing_url: "https://www.exhibitionglobe.com/..."
  event_card:  ".expo-listing"
  name:        "h3.title"
  venue:       ".location"
  date:        ".dates"
```

---

## 10. Python Packages / Dependencies

### `requirements.txt`
```txt
# --- HTTP & parsing ---
requests==2.32.3
httpx==0.27.2
beautifulsoup4==4.12.3
lxml==5.3.0
pyyaml==6.0.2

# --- Dynamic pages ---
selenium==4.25.0
webdriver-manager==4.0.2
playwright==1.47.0

# --- Data ---
pandas==2.2.3
numpy==2.1.1
pydantic==2.9.2

# --- Database ---
SQLAlchemy==2.0.35
alembic==1.13.3
psycopg2-binary==2.9.9   # only if using Postgres

# --- Dashboard ---
streamlit==1.39.0
plotly==5.24.1

# --- Config & logging ---
python-dotenv==1.0.1
loguru==0.7.2

# --- Scheduling ---
APScheduler==3.10.4

# --- Dev / tests ---
pytest==8.3.3
pytest-mock==3.14.0
responses==0.25.3
ruff==0.6.9
black==24.10.0
mypy==1.11.2
```

### Install Commands
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

---

## 11. Dashboard Architecture

**Framework:** Streamlit (multi-page)

| Page | File | Purpose |
|---|---|---|
| Overview | `pages/1_Overview.py` | KPI cards (total expos, cities, upcoming), charts |
| Expo List | `pages/2_Expo_List.py` | Dataframe with filters (city, category, date, fee) + CSV download |
| Expo Detail | `pages/3_Expo_Detail.py` | Single event drill-down |

**Common components:**
- Sidebar filters (city multiselect, category, date range, fee slider)
- Search box (name/description)
- Cached DB queries via `@st.cache_data(ttl=600)`
- Export to CSV / Excel button

**Launch:**
```bash
streamlit run dashboard/app.py
```

---

## 12. Scheduling & Automation

### Option A — Cron (Linux/macOS)
```bash
0 2 * * * cd /path/to/expo-scraper && venv/bin/python scheduler/run_all.py >> logs/cron.log 2>&1
```

### Option B — Windows Task Scheduler
- Program: `C:\path\to\expo-scraper\venv\Scripts\python.exe`
- Arguments: `scheduler\run_all.py`
- Trigger: Daily 02:00

### Option C — APScheduler (in-process)
```python
from apscheduler.schedulers.blocking import BlockingScheduler
from scheduler.run_all import run_all

sched = BlockingScheduler()
sched.add_job(run_all, "cron", hour=2, minute=0)
sched.start()
```

---

## 13. Logging & Error Handling

- **`utils/logger.py`** sets up `loguru` with:
  - Console output (colored)
  - Rotating file: `logs/scraper_{time}.log` (10 MB, 7-day retention)
- Each scraper logs: start URL, records found, errors, duration.
- Failed pages → retried `MAX_RETRIES` times with exponential backoff.
- Final failure → logged + skipped (does not crash the pipeline).
- **Change detection:** store `hash(name + venue + start_date)` to detect
  duplicate / updated events without re-inserting.

---

## 14. Testing Strategy

| Test Type | Tool | Scope |
|---|---|---|
| Unit | `pytest` | `cleaner.py`, `normalizer.py`, parsers |
| Mock HTTP | `responses` | Scrapers against saved HTML fixtures |
| Integration | `pytest` | Full scrape → DB → query round-trip |
| Dashboard smoke | `streamlit.testing` | Ensure pages render without error |

Test fixtures stored in `tests/fixtures/*.html`.

Run: `pytest -v`

---

## 15. Security, Legal & Ethical Considerations

1. **`robots.txt`** — Always fetch and honor before scraping any path.
2. **Terms of Service** — Eventbrite, for example, forbids scraping → use
   their official **API** instead.
3. **Rate limiting** — Minimum 1–2 s delay between requests.
4. **User-Agent** — Identify your bot with contact info.
5. **Personal data** — Do **not** scrape personal emails/phones unless public
   and permitted.
6. **Secrets** — `.env` in `.gitignore`, never commit API keys.
7. **Copyright** — Store only facts (name, date, venue); do not republish
   copyrighted descriptions verbatim — paraphrase or link.

---

## 16. Deployment

### Local Development
```bash
python main.py --site 10times
streamlit run dashboard/app.py
```

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "scheduler/run_all.py"]
```

```yaml
# docker-compose.yml
services:
  scraper:
    build: .
    env_file: .env
    volumes:
      - ./data:/app/data
  dashboard:
    build: .
    command: streamlit run dashboard/app.py --server.port=8501 --server.address=0.0.0.0
    ports:
      - "8501:8501"
    volumes:
      - ./data:/app/data
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: expo
      POSTGRES_PASSWORD: expo
      POSTGRES_DB: expo_db
    volumes:
      - pgdata:/var/lib/postgresql/data
volumes:
  pgdata:
```

### Production Options
- **Scraper** → VPS cron / GitHub Actions / AWS Lambda + EventBridge
- **DB** → Managed Postgres (Supabase / RDS / Neon)
- **Dashboard** → Streamlit Community Cloud / Render / Railway / Fly.io

---

## 17. Future Roadmap

- [ ] Add 5 more scrapers (TradeIndia, ITPO, Eventseye, etc.)
- [ ] NLP-based category classifier (technical vs non-technical)
- [ ] Email digest of new expos (weekly)
- [ ] Map view of expos (Plotly / Folium)
- [ ] REST API (FastAPI) on top of the DB
- [ ] Multi-language support (Hindi, regional)
- [ ] ML-based deduplication across sources
- [ ] User accounts + saved filters

---

## 📌 Quick Reference

| Command | Purpose |
|---|---|
| `python main.py --site 10times` | Run one scraper |
| `python scheduler/run_all.py` | Run all scrapers |
| `streamlit run dashboard/app.py` | Launch dashboard |
| `pytest -v` | Run tests |
| `ruff check .` | Lint |
| `black .` | Format |
| `mypy .` | Type check |

---

*End of document.*
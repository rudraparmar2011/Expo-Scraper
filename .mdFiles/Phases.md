# 📆 Development Phases — Expo Scraper & Dashboard

> A pragmatic, phase-by-phase roadmap to build the project from scratch.
> Each phase is **self-contained**, ends with a **runnable deliverable**, and
> builds on the previous one. Estimated time is for a solo dev learning as
> they go — adjust as needed.

**Total estimated time:** 6–9 weeks (part-time) · 2–3 weeks (full-time)

---

## 📑 Phase Index

| # | Phase | Deliverable | Est. Time |
|---|---|---|---|
| 0 | Environment Setup | Working project skeleton | ½ day |
| 1 | Base Scraper + 1st Source | CLI runs, scrapes 10times | 2–3 days |
| 2 | Parser & Cleaner | Clean, validated dicts | 1–2 days |
| 3 | Database Layer | SQLite with dedupe | 1–2 days |
| 4 | CLI Orchestration | `python main.py --site …` end-to-end | 1 day |
| 5 | Dashboard MVP | Streamlit reads DB & shows table | 2 days |
| 6 | Multi-Source Expansion | 3–5 more scrapers | 4–6 days |
| 7 | Advanced Dashboard | Filters, charts, detail page, export | 2–3 days |
| 8 | Logging, Tests, Config | Production hygiene | 2–3 days |
| 9 | Automation & Scheduling | Runs daily unattended | 1 day |
| 10 | Deployment | Docker + hosted dashboard | 2–4 days |
| 11 | Polish & Roadmap | Docs, NLP classifier, extras | ongoing |

---

## 🧱 Phase 0 — Environment Setup

**Goal:** Have the folder skeleton, virtualenv, and dependencies installed.

### Tasks
- [ ] Create the project folder structure (see `PROJECT_ARCHITECTURE.md` §5)
- [ ] `python -m venv venv` and activate it
- [ ] Create `requirements.txt` (start minimal, expand per phase)
- [ ] `pip install -r requirements.txt`
- [ ] Init git: `git init`, first commit
- [ ] Create `.gitignore` (venv, `.env`, `data/`, `logs/`, `__pycache__`)
- [ ] Create `PROJECT_ARCHITECTURE.md` and `PHASES.md`
- [ ] Open project in VS Code / PyCharm

### Deliverable
✅ Empty but correct project structure; deps installed; git committed.

### Files Touched
`requirements.txt`, `.gitignore`, `PROJECT_ARCHITECTURE.md`, `PHASES.md`

### Test
```bash
python -c "import requests, bs4, pandas, streamlit; print('OK')"
```

---

## 🕸️ Phase 1 — Base Scraper + First Source (10times)

**Goal:** Scrape one website and print results to console.

### Tasks
- [ ] Create `config/settings.py` (paths, delay, user-agent)
- [ ] Create `config/selectors.yaml` (10times selectors)
- [ ] Create `utils/logger.py` (loguru setup)
- [ ] Create `scrapers/base_scraper.py`
  - Session with headers
  - `fetch(url)` with retries + delay
  - `robots.txt` check helper
- [ ] Open `10times.com` in browser → inspect HTML (F12)
- [ ] Create `scrapers/ten_times.py` with `scrape()` function
  - Fetch listing page
  - Loop over event cards
  - Extract: name, venue, date, link, description
- [ ] Run manually: `python -c "from scrapers.ten_times import scrape; print(scrape()[:2])"`
- [ ] Save raw output to `data/raw/ten_times_YYYYMMDD.json`

### Deliverable
✅ Raw list of dicts from 10times written to `data/raw/`.

### Files Touched
`config/settings.py`, `config/selectors.yaml`, `utils/logger.py`,
`scrapers/base_scraper.py`, `scrapers/ten_times.py`

### Test
```bash
python -c "from scrapers.ten_times import scrape; print(len(scrape()))"
# Expect: > 0
```

### 🚧 Common Blockers
- CSS selectors wrong → re-inspect DOM
- Site blocks requests → add realistic `User-Agent`
- JS-rendered → fall back to Selenium in a later phase

---

## 🧹 Phase 2 — Parser & Cleaner

**Goal:** Turn messy raw strings into clean, typed records.

### Tasks
- [ ] Create `parsers/cleaner.py`
  - `clean_fee("₹5,000/-") → (5000, "INR")`
  - `parse_date_range("15–18 Oct 2026") → (date, date)`
  - `strip_html`, `squash_whitespace`
- [ ] Create `parsers/normalizer.py`
  - Canonical cities (`Bombay → Mumbai`)
  - Category inference (technical vs non-technical)
- [ ] Create Pydantic model `Expo` in `parsers/models.py`
- [ ] Wire cleaner → normalizer → validation in a `process(raw)` function
- [ ] Add unit tests in `tests/test_parsers.py`

### Deliverable
✅ `process(raw_dict) → Expo` works; parsers are tested.

### Files Touched
`parsers/cleaner.py`, `parsers/normalizer.py`, `parsers/models.py`,
`tests/test_parsers.py`

### Test
```bash
pytest tests/test_parsers.py -v
```

---

## 💾 Phase 3 — Database Layer

**Goal:** Persist cleaned records into SQLite with dedupe & updates.

### Tasks
- [ ] Create `utils/database.py`
  - SQLAlchemy engine + `Session`
  - `ExpoTable` ORM model (see architecture §7.1)
  - `init_db()` — create tables
  - `save_expos(list[Expo])` — upsert on `source_url`
  - `get_expos(filters)` — query builder
- [ ] Add `data/expo.db` (gitignored)
- [ ] Add `tests/test_database.py` (insert → query → assert)
- [ ] Add `utils/helpers.py → event_hash()` for change detection

### Deliverable
✅ Running scrape populates SQLite; re-running doesn't duplicate rows.

### Files Touched
`utils/database.py`, `utils/helpers.py`, `tests/test_database.py`

### Test
```bash
python -c "from utils.database import init_db, get_expos; init_db(); print(get_expos())"
```

---

## 🎛️ Phase 4 — CLI Orchestration

**Goal:** One command runs the whole pipeline end-to-end.

### Tasks
- [ ] Create `main.py` with `argparse`
  - `--site {10times,…}`
  - `--output {db,csv,both}`
  - `--limit N`
- [ ] Pipeline: scrape → clean → validate → save
- [ ] Print summary: `Scraped 42, saved 40, skipped 2`
- [ ] Export snapshot to `data/processed/expos_YYYYMMDD.csv`

### Deliverable
✅ `python main.py --site 10times` works end-to-end.

### Files Touched
`main.py`

### Test
```bash
python main.py --site 10times
ls data/processed/
```

---

## 📊 Phase 5 — Dashboard MVP

**Goal:** A working Streamlit app that reads the DB and shows data.

### Tasks
- [ ] Create `dashboard/app.py`
  - Page config (title, wide layout)
  - Load data via `get_expos()`
  - KPI cards: total expos, cities, upcoming
- [ ] Create `dashboard/pages/2_Expo_List.py`
  - `st.dataframe` with all expos
  - Sidebar: city filter, category filter, search box
  - CSV download button
- [ ] Cache queries with `@st.cache_data(ttl=600)`
- [ ] Launch: `streamlit run dashboard/app.py`

### Deliverable
✅ Browser at `localhost:8501` shows filterable expo list.

### Files Touched
`dashboard/app.py`, `dashboard/pages/2_Expo_List.py`

### Test
```bash
streamlit run dashboard/app.py
# Open http://localhost:8501
```

---

## 🌐 Phase 6 — Multi-Source Expansion

**Goal:** Add 3–5 more scrapers (or APIs).

### Tasks (repeat per source)
- [ ] Inspect site HTML / find API
- [ ] Add selectors to `config/selectors.yaml`
- [ ] Create `scrapers/<source>.py` with `scrape()`
- [ ] Register in `main.py` `SCRAPER_MAP`
- [ ] Handle pagination
- [ ] Add fixture + test in `tests/test_scrapers.py`
- [ ] Verify dedupe across sources works

### Suggested Order
1. **ExhibitionGlobe** — simple, clean HTML
2. **Expolume** — directory site
3. **MeraEvents** — India-focused
4. **Eventbrite** — use **API**, not scraping
5. **Sumvaad** — B2B, India

### Deliverable
✅ ≥ 4 sources merged into a single DB.

### Files Touched
`scrapers/*.py`, `config/selectors.yaml`, `main.py`, `tests/test_scrapers.py`

### Test
```bash
python scheduler/run_all.py    # or loop over sites manually
python -c "from utils.database import get_expos; print(len(get_expos()))"
```

---

## 🎨 Phase 7 — Advanced Dashboard

**Goal:** Rich UX — charts, detail page, exports.

### Tasks
- [ ] `pages/1_Overview.py`
  - Plotly: expos per city, per month, per category
  - Timeline chart of upcoming events
- [ ] `pages/3_Expo_Detail.py`
  - Select event → full detail card
  - Map (Plotly / Folium) if lat/long available
- [ ] Advanced filters: date range, fee slider, source
- [ ] Export to Excel (`openpyxl`)
- [ ] Custom CSS in `dashboard/assets/style.css`

### Deliverable
✅ Multi-page dashboard with visual analytics.

### Files Touched
`dashboard/pages/1_Overview.py`, `dashboard/pages/3_Expo_Detail.py`,
`dashboard/assets/style.css`

---

## 🧪 Phase 8 — Logging, Tests, Config Polish

**Goal:** Make the project production-grade.

### Tasks
- [ ] Rotating log files in `logs/` (10 MB, 7-day retention)
- [ ] Structured logs per scraper (start, count, duration, errors)
- [ ] Fixtures for every scraper (`tests/fixtures/*.html`)
- [ ] Mock HTTP with `responses` (no live calls in tests)
- [ ] `ruff`, `black`, `mypy` configs in `pyproject.toml`
- [ ] Coverage ≥ 70% on parsers/cleaners
- [ ] `pre-commit` hooks (ruff + black)

### Deliverable
✅ Green CI locally; consistent code style.

### Files Touched
`utils/logger.py`, `tests/`, `pyproject.toml`, `.pre-commit-config.yaml`

### Test
```bash
pytest -v --cov=scrapers --cov=parsers
ruff check .
black --check .
mypy .
```

---

## ⏰ Phase 9 — Automation & Scheduling

**Goal:** Data refreshes daily without you.

### Tasks
- [ ] `scheduler/run_all.py` — runs every scraper, logs summary
- [ ] Choose scheduler:
  - **Linux/macOS:** `crontab -e` → `0 2 * * *`
  - **Windows:** Task Scheduler
  - **In-app:** APScheduler (see architecture §12)
- [ ] Email / Slack notification on completion (optional)
- [ ] Alert on scraper failure (email / Telegram bot)

### Deliverable
✅ New data appears in DB every morning automatically.

### Files Touched
`scheduler/run_all.py`, `cron` file or Task Scheduler entry

---

## 🚀 Phase 10 — Deployment

**Goal:** Public dashboard + automated scraping in the cloud.

### Tasks
- [ ] Write `Dockerfile` + `docker-compose.yml`
- [ ] Local test: `docker compose up --build`
- [ ] Move DB to Postgres (Supabase / Neon / RDS)
- [ ] Deploy dashboard to **Streamlit Community Cloud** (easiest)
- [ ] Deploy scraper to:
  - GitHub Actions (cron) — free & simple
  - OR VPS with cron
  - OR AWS Lambda + EventBridge
- [ ] Add HTTPS + domain (optional)

### Deliverable
✅ Public URL like `expo-dashboard.streamlit.app` with fresh daily data.

### Files Touched
`Dockerfile`, `docker-compose.yml`, `.github/workflows/scrape.yml`

---

## ✨ Phase 11 — Polish & Future Roadmap

**Goal:** Nice-to-haves and long-term value.

### Tasks
- [ ] NLP category classifier (technical vs non-technical)
- [ ] ML-based dedupe across sources
- [ ] FastAPI REST endpoint on top of DB
- [ ] Weekly email digest of new expos
- [ ] Map view of all expos
- [ ] Multi-language support (Hindi / regional)
- [ ] User accounts + saved filters
- [ ] Public API docs (Swagger)

### Deliverable
✅ Continuous improvements — pick items as time allows.

---

## 🗓️ Suggested Weekly Plan (Part-Time, ~2h/day)

| Week | Focus | Phases |
|---|---|---|
| 1 | Skeleton, first scraper | 0, 1 |
| 2 | Cleaners, DB, CLI | 2, 3, 4 |
| 3 | Dashboard MVP | 5 |
| 4 | Add 2–3 more scrapers | 6 |
| 5 | Advanced dashboard | 7 |
| 6 | Tests, logging, polish | 8 |
| 7 | Automation + deploy | 9, 10 |
| 8+ | Extras & maintenance | 11 |

---

## ✅ Milestone Checklist

- [ ] **M1 (end Phase 4):** CLI scrapes 10times → SQLite, dedupe works
- [ ] **M2 (end Phase 5):** Streamlit shows data at `localhost:8501`
- [ ] **M3 (end Phase 6):** ≥ 4 sources in one unified DB
- [ ] **M4 (end Phase 8):** Tested, linted, logged
- [ ] **M5 (end Phase 10):** Public dashboard + daily cron

---

## 💡 Rules of Thumb

1. **Finish a phase before starting the next.** No half-done scrapers.
2. **Every phase ends with a runnable command.** If you can't demo it, it's not done.
3. **Commit at the end of every phase** (`git commit -m "phase N: …"`).
4. **Write the test while the code is fresh**, not later.
5. **Respect `robots.txt` & ToS** at every phase — no shortcuts.
6. **Keep raw data dumps** so you can re-parse without re-scraping.

---

## 🎯 Start Here

> Ready? Open **Phase 0** tasks and knock them out today.
> When Phase 0 is done, ping me and I'll write the actual code for **Phase 1**:
> `config/settings.py`, `scrapers/base_scraper.py`, `scrapers/ten_times.py`,
> and `utils/logger.py` — everything you need to run your first real scrape.

---

*End of document.*
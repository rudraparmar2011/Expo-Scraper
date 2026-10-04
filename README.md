# 🏛️ Expo Scraper & Dashboard

Scrapes all technical & non-technical expos in **Ahmedabad** and **Vadodara**
from public sources and serves them via an interactive Streamlit dashboard.

---

## ✨ Features

- **Multi-source scraper** — Exhibition Globe (more coming)
- **Automatic classification** — Technical / Non-Technical, 13 sub-categories
- **Prose extraction** — dates, venues, fees, cities parsed from article text
- **SQLite storage** — with deduplication on `source_url`
- **Filterable dashboard** — search, filter by city/category, download CSV
- **Ethical scraping** — respects `robots.txt`, uses rate limits, identifies itself

---

## 🚀 Quick Start

```bash
# 1. Clone + setup
git clone https://github.com/rudraparmar2011/Expo-Scraper.git
cd expo-scraper
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure
copy .env.example .env       # Windows
cp .env.example .env         # macOS/Linux

# 4. Scrape data
python main.py --site exhibition_globe

# 5. Launch dashboard
streamlit run dashboard/app.py
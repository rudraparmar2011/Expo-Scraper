"""
dashboard/app.py
----------------
Streamlit home page for the Expo Scraper project.
"""
from __future__ import annotations

import sys
from pathlib import Path

# --- Bootstrap: allow imports from project root ---
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

# --- Page config FIRST (before any other Streamlit call) ---
st.set_page_config(
    page_title="Expo Dashboard — Ahmedabad & Vadodara",
    page_icon="🏛️",
    layout="wide",
)

# --- Apply custom CSS ---
from dashboard._style import apply_css  # noqa: E402

apply_css()

# --- Content ---
st.title("🏛️ Expo Dashboard")
st.caption("All technical & non-technical expos in **Ahmedabad** and **Vadodara**")

st.markdown("""
### Welcome!

Use the sidebar to navigate:

- **📊 Overview** — KPIs, charts, and insights
- **📋 Expo List** — filterable table with all expos
- **🔎 Expo Detail** — full details of a single expo

---

### About

This dashboard aggregates data scraped from public sources.
Built with **Streamlit**, **SQLAlchemy**, and a custom Python scraping pipeline.
""")

# --- Quick stats ---
try:
    from utils.database import count_expos, list_cities, list_categories

    col1, col2, col3 = st.columns(3)
    col1.metric("📊 Total Expos", count_expos())
    col2.metric("🏙️ Cities", len(list_cities()))
    col3.metric("🏷️ Categories", len(list_categories()))
except Exception as e:
    st.error(f"Could not load stats: {e}")
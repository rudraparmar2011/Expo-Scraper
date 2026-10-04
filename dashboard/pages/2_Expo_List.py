"""
dashboard/pages/2_Expo_List.py
------------------------------
Filterable table of all expos with CSV download.
"""
from __future__ import annotations

import sys
from pathlib import Path

from dashboard._style import apply_css
apply_css()

# --- Bootstrap ---
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from utils.database import get_expos, list_categories, list_cities  # noqa: E402

st.set_page_config(page_title="Expo List", page_icon="📋", layout="wide")
st.title("📋 Expo List")


@st.cache_data(ttl=60)
def load_data() -> pd.DataFrame:
    records = get_expos()
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    for col in ("start_date", "end_date"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


@st.cache_data(ttl=60)
def get_options():
    return {
        "cities": list_cities(),
        "categories": list_categories(),
    }


df = load_data()
options = get_options()

if df.empty:
    st.warning("No data in the database yet.")
    st.code("python main.py --site exhibition_globe", language="bash")
    st.stop()

# ---------------- Sidebar filters ----------------
st.sidebar.header("🔍 Filters")

all_cities = options["cities"] or sorted(df["city"].dropna().unique().tolist())
selected_cities = st.sidebar.multiselect("City", all_cities, default=all_cities)

all_categories = options["categories"] or sorted(df["category"].dropna().unique().tolist())
selected_categories = st.sidebar.multiselect("Category", all_categories, default=all_categories)

search_text = st.sidebar.text_input("Search name / venue", "")

# ---------------- Apply filters ----------------
filtered = df.copy()

if selected_cities:
    filtered = filtered[filtered["city"].isin(selected_cities)]

if selected_categories:
    filtered = filtered[filtered["category"].isin(selected_categories)]

if search_text:
    mask = (
        filtered["name"].str.contains(search_text, case=False, na=False)
        | filtered["venue"].fillna("").str.contains(search_text, case=False, na=False)
    )
    filtered = filtered[mask]

# ---------------- Results ----------------
st.write(f"**{len(filtered)}** expos match your filters")

# Build a display-friendly copy
display_cols = [
    "name", "city", "category", "sub_category",
    "start_date", "end_date", "venue", "fees", "source_url",
]
available = [c for c in display_cols if c in filtered.columns]
table = filtered[available].copy()

# -------- Clean NaN for display --------
# 1. Dates: convert NaT to None, then format as string
for col in ("start_date", "end_date"):
    if col in table.columns:
        table[col] = table[col].apply(
            lambda d: d.strftime("%d %b %Y") if pd.notna(d) else "—"
        )

# 2. Fees: NaN → "—", else format
if "fees" in table.columns:
    table["fees"] = table["fees"].apply(
        lambda x: f"{x:,.0f}" if pd.notna(x) else "—"
    )

# 3. Text columns: NaN → "—"
for col in ("city", "category", "sub_category", "venue", "name"):
    if col in table.columns:
        table[col] = table[col].fillna("—")

# 4. Rename for display
table = table.rename(columns={
    "name": "Name",
    "city": "City",
    "category": "Category",
    "sub_category": "Sub-category",
    "start_date": "Start",
    "end_date": "End",
    "venue": "Venue",
    "fees": "Fees (₹)",
    "source_url": "Source",
})

st.dataframe(
    table,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Source": st.column_config.LinkColumn("Source", display_text="Open"),
    },
)

# ---------------- CSV download ----------------
csv = filtered.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Download CSV",
    data=csv,
    file_name="expos.csv",
    mime="text/csv",
)
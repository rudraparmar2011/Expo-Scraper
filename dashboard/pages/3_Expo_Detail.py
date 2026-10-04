"""
dashboard/pages/3_Expo_Detail.py
--------------------------------
Full details of a single expo — NaN-safe rendering.
"""
from __future__ import annotations

import sys
from pathlib import Path

from dashboard._style import apply_css
apply_css()

# --- Bootstrap: allow imports from project root ---
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from utils.database import get_expos  # noqa: E402

st.set_page_config(page_title="Expo Detail", page_icon="🔎", layout="wide")
st.title("🔎 Expo Detail")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def show(value, fallback: str = "—") -> str:
    """Return a clean display string, or fallback if the value is empty/NaN."""
    if value is None:
        return fallback
    if isinstance(value, float) and pd.isna(value):
        return fallback
    if isinstance(value, str) and not value.strip():
        return fallback
    try:
        if pd.isna(value):
            return fallback
    except (TypeError, ValueError):
        pass
    return str(value)


def fmt_date(value) -> str:
    """Format a date/datetime as '15 Sep 2026', or '—'."""
    if value is None or pd.isna(value):
        return "—"
    try:
        return pd.to_datetime(value).strftime("%d %b %Y")
    except Exception:
        return "—"


def fmt_fees(value, currency: str = "") -> str:
    """Format fee as '5,000 INR' or 'Not specified'."""
    if value is None or pd.isna(value):
        return "Not specified"
    try:
        return f"{float(value):,.0f} {currency}".strip()
    except (TypeError, ValueError):
        return "Not specified"


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
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


df = load_data()

if df.empty:
    st.warning("No data in the database yet.")
    st.code("python main.py --site exhibition_globe", language="bash")
    st.stop()


# ---------------------------------------------------------------------------
# Sidebar — filters
# ---------------------------------------------------------------------------
st.sidebar.header("🔍 Filter")

cities = sorted(df["city"].dropna().unique().tolist()) or ["—"]
selected_city = st.sidebar.selectbox("City", ["All"] + cities)

categories = sorted(df["category"].dropna().unique().tolist()) or ["—"]
selected_category = st.sidebar.selectbox("Category", ["All"] + categories)

# Apply
pool = df.copy()
if selected_city != "All":
    pool = pool[pool["city"] == selected_city]
if selected_category != "All":
    pool = pool[pool["category"] == selected_category]

if pool.empty:
    st.warning("No expos match your filters.")
    st.stop()


# ---------------------------------------------------------------------------
# Selector
# ---------------------------------------------------------------------------
names = sorted(pool["name"].dropna().unique().tolist())
chosen = st.selectbox("Pick an expo", names)
row = pool[pool["name"] == chosen].iloc[0]

st.markdown("---")


# ---------------------------------------------------------------------------
# Detail card
# ---------------------------------------------------------------------------
col_a, col_b = st.columns([2, 1])

with col_a:
    st.subheader(show(row.get("name")))

    desc = show(row.get("description"), "")
    if desc:
        st.write(desc)

    # Location
    st.markdown("##### 📍 Location")
    st.write(f"**Venue:** {show(row.get('venue'))}")
    st.write(f"**City:** {show(row.get('city'))}")
    st.write(f"**State:** {show(row.get('state'))}")
    st.write(f"**Country:** {show(row.get('country'))}")

    # Dates
    st.markdown("##### 📅 Dates")
    st.write(f"**Start:** {fmt_date(row.get('start_date'))}")
    st.write(f"**End:** {fmt_date(row.get('end_date'))}")

    # Classification
    st.markdown("##### 🏷️ Classification")
    st.write(f"**Category:** {show(row.get('category'))}")
    st.write(f"**Sub-category:** {show(row.get('sub_category'))}")

    # Fees
    st.markdown("##### 💰 Fees")
    st.write(fmt_fees(row.get("fees"), show(row.get("currency"), "")))

    # Organizer (if available)
    organizer = show(row.get("organizer"), "")
    if organizer:
        st.markdown("##### 👤 Organizer")
        st.write(organizer)

    # Contact
    email = show(row.get("contact_email"), "")
    phone = show(row.get("contact_phone"), "")
    if email or phone:
        st.markdown("##### 📞 Contact")
        if email:
            st.write(f"**Email:** {email}")
        if phone:
            st.write(f"**Phone:** {phone}")

with col_b:
    img = row.get("image_url")
    if isinstance(img, str) and img.strip():
        try:
            st.image(img, use_column_width=True)
        except Exception:
            st.caption("_(image unavailable)_")

    st.markdown("##### 🔗 Source")
    src = row.get("source_url")
    if isinstance(src, str) and src.strip():
        st.link_button("Open original page", src)
        st.caption(f"`{src[:80]}{'…' if len(src) > 80 else ''}`")

    st.markdown("##### 🏢 Source")
    st.write(show(row.get("source")))



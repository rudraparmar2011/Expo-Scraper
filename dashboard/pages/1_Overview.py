"""
dashboard/pages/1_Overview.py
-----------------------------
Overview: KPIs, charts, and insights.
"""
from __future__ import annotations

import sys
from pathlib import Path

# --- Bootstrap: allow imports from project root ---
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402

# --- Page config FIRST ---
st.set_page_config(page_title="Overview", page_icon="📊", layout="wide")

# --- Apply custom CSS ---
from dashboard._style import apply_css  # noqa: E402

apply_css()

# --- Data ---
from utils.database import get_expos  # noqa: E402


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

# --- Title ---
st.title("📊 Overview")

if df.empty:
    st.warning("No data in the database yet.")
    st.code("python main.py --site exhibition_globe", language="bash")
    st.stop()

# ---------------- KPIs ----------------
col1, col2, col3, col4 = st.columns(4)
col1.metric("📊 Total Expos", len(df))
col2.metric("🏙️ Cities", df["city"].nunique())
col3.metric("🔧 Technical", len(df[df["category"] == "Technical"]))
col4.metric("🎨 Non-Technical", len(df[df["category"] == "Non-Technical"]))

st.markdown("---")

# ---------------- Charts ----------------
c1, c2 = st.columns(2)

with c1:
    city_counts = df["city"].value_counts().reset_index()
    city_counts.columns = ["City", "Count"]
    fig = px.bar(
        city_counts, x="City", y="Count",
        title="Expos per City",
        color="City",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    st.plotly_chart(fig, use_container_width=True)

with c2:
    df_cats = df.copy()
    df_cats["category"] = df_cats["category"].fillna("Uncategorised")
    df_cats["sub_category"] = df_cats["sub_category"].fillna("Other")
    cat_counts = (
        df_cats.groupby(["category", "sub_category"])
        .size()
        .reset_index(name="Count")
    )
    fig = px.sunburst(
        cat_counts,
        path=["category", "sub_category"],
        values="Count",
        title="Expos by Category",
        color_discrete_sequence=px.colors.qualitative.Pastel,
    )
    st.plotly_chart(fig, use_container_width=True)

# ---------------- Timeline ----------------
if "start_date" in df.columns:
    upcoming = df.dropna(subset=["start_date"]).copy()
    upcoming["city"] = upcoming["city"].fillna("Unknown")
    upcoming = upcoming.sort_values("start_date")

    if not upcoming.empty:
        st.markdown("### 📅 Timeline")
        fig = px.scatter(
            upcoming,
            x="start_date", y="city",
            color="category",
            hover_name="name",
            hover_data=["venue", "sub_category"],
            title="Upcoming Expos",
        )
        st.plotly_chart(fig, use_container_width=True)
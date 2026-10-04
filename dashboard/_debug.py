"""Minimal debug dashboard — no filters, no caching, no fancy stuff."""
import sys
from pathlib import Path

import streamlit as st

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

st.title("DEBUG DASHBOARD")

# 1. Show paths
st.header("1. Paths")
st.write(f"CWD: `{Path.cwd()}`")
st.write(f"Project root: `{ROOT}`")

db_file = ROOT / "data" / "expo.db"
st.write(f"DB file: `{db_file}`")
st.write(f"DB exists: `{db_file.exists()}`")
if db_file.exists():
    st.write(f"DB size: `{db_file.stat().st_size}` bytes")

# 2. Try importing + querying directly
st.header("2. Direct DB query")
try:
    from utils.database import count_expos, get_expos
    st.write(f"Total rows: `{count_expos()}`")
    rows = get_expos()
    st.write(f"get_expos() returns: `{len(rows)}` rows")
    if rows:
        st.write("First row:", rows[0])
except Exception as e:
    st.error(f"Failed: {type(e).__name__}: {e}")
    st.exception(e)

# 3. Show raw table
st.header("3. Raw data table")
try:
    import pandas as pd
    rows = get_expos()
    if rows:
        df = pd.DataFrame(rows)
        st.write(f"DataFrame shape: `{df.shape}`")
        st.dataframe(df)
    else:
        st.warning("No rows returned")
except Exception as e:
    st.error(f"Failed: {type(e).__name__}: {e}")
    st.exception(e)
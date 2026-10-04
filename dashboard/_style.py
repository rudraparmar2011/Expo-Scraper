"""dashboard/_style.py — shared CSS loader."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

_CSS_PATH = Path(__file__).resolve().parent / "assets" / "style.css"


def apply_css() -> None:
    """Inject the project stylesheet into the current Streamlit page."""
    if not _CSS_PATH.exists():
        st.warning(f"⚠️ Stylesheet not found at: {_CSS_PATH}")
        return

    try:
        css = _CSS_PATH.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"Could not load stylesheet: {e}")
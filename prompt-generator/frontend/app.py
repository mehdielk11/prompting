"""Streamlit entry point — single shell with st.navigation().

Theme + sidebar are injected ONCE here and never re-rendered on page
changes, eliminating the sidebar flicker / re-render on navigation.
"""

import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_BASE = os.getenv("STREAMLIT_API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Générateur de Prompts Audio",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Store API base URL in session state so pages can access it
if "api_base" not in st.session_state:
    st.session_state["api_base"] = API_BASE

# ---------------------------------------------------------------------------
# Navigation — define pages and let Streamlit handle routing
# ---------------------------------------------------------------------------
home_page = st.Page(
    "pages/home.py",
    title="Accueil",
    icon="🏠",
    default=True,
)
generate_page = st.Page(
    "pages/generate.py",
    title="Générer",
    icon="✨",
)
library_page = st.Page(
    "pages/library.py",
    title="Bibliothèque",
    icon="📚",
)

pg = st.navigation(
    [home_page, generate_page, library_page],
    position="hidden",  # we render nav ourselves in render_sidebar()
)

# ---------------------------------------------------------------------------
# Theme + sidebar — injected ONCE, never re-runs on page navigation
# ---------------------------------------------------------------------------
from frontend.theme import (  # noqa: E402
    inject_theme,
    render_sidebar,
)

inject_theme()
render_sidebar()

pg.run()

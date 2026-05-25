"""Home page content — hero + feature cards + API status."""

import os

import streamlit as st

from frontend.theme import (
    api_status_pill,
    feature_card,
    gradient_divider,
    gradient_text,
    hero_section,
)

API_BASE = st.session_state.get("api_base", os.getenv("STREAMLIT_API_BASE_URL", "http://localhost:8000"))

# ---------------------------------------------------------------------------
# Hero section
# ---------------------------------------------------------------------------
st.markdown(
    hero_section(
        title_html=f"Créez des prompts audio {gradient_text('professionnels')}",
        subtitle=(
            "Générez, optimisez et gérez des prompts de haute qualité "
            "pour la synthèse vocale, la musique et les effets sonores — "
            "propulsé par l'intelligence artificielle."
        ),
    ),
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Feature cards
# ---------------------------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    st.markdown(
        feature_card(
            icon="<svg width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><polygon points='13 2 3 14 12 14 11 22 21 10 12 10 13 2'/></svg>",
            title="Génération IA",
            description="Décrivez votre besoin en langage naturel et obtenez un prompt structuré et optimisé en quelques secondes.",
            icon_bg="rgba(99,102,241,0.12)",
            icon_color="#6366f1",
        ),
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        feature_card(
            icon="<svg width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M4 19.5A2.5 2.5 0 0 1 6.5 17H20'/><path d='M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z'/></svg>",
            title="Bibliothèque",
            description="Sauvegardez, recherchez et organisez vos meilleurs prompts avec tags, scores et historique de versions.",
            icon_bg="rgba(6,182,212,0.12)",
            icon_color="#06b6d4",
        ),
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# API status
# ---------------------------------------------------------------------------
st.markdown(gradient_divider(), unsafe_allow_html=True)
st.markdown(api_status_pill(API_BASE), unsafe_allow_html=True)

"""Streamlit entry point — configures the app and shared API client."""

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

st.title("🎙️ Générateur de Prompts Audio")
st.markdown(
    """
    Bienvenue sur la plateforme de génération automatique de prompts professionnels pour l'audio.

    Utilisez le menu de gauche pour naviguer entre les pages :
    - **Générer** — créez un prompt à partir d'une description libre
    - **Bibliothèque** — gérez vos prompts sauvegardés
    - **Analytics** — visualisez vos statistiques
    """
)

st.info(f"API connectée sur : `{API_BASE}`")

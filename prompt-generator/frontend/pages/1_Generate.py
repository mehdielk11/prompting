"""Page 1 — Generate a professional audio prompt."""

from __future__ import annotations

import requests
import streamlit as st

API_BASE = st.session_state.get("api_base", "http://localhost:8000")

st.set_page_config(page_title="Générer un Prompt", page_icon="✨", layout="wide")
st.title("✨ Générer un Prompt Audio")

# ---------------------------------------------------------------------------
# Input form
# ---------------------------------------------------------------------------

with st.form("generate_form"):
    description = st.text_area(
        "Décrivez votre besoin audio :",
        placeholder="Ex: Une voix féminine chaleureuse pour une introduction e-learning sur la cybersécurité...",
        height=120,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        audio_type = st.selectbox("Type audio", ["tts", "music", "sfx", "voiceover"])
    with col2:
        tone = st.selectbox(
            "Ton / Style",
            ["professional", "neutral", "dramatic", "warm", "energetic", "calm", "playful"],
        )
    with col3:
        duration = st.selectbox("Durée estimée", ["short", "medium", "long"])

    submitted = st.form_submit_button("✨ Générer le Prompt", use_container_width=True)

# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

if submitted:
    if not description.strip():
        st.error("Veuillez entrer une description.")
    else:
        with st.spinner("Génération en cours…"):
            try:
                resp = requests.post(
                    f"{API_BASE}/api/generate",
                    json={
                        "description": description,
                        "type": audio_type,
                        "tone": tone,
                        "duration": duration,
                    },
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                st.session_state["last_generated"] = data
            except requests.exceptions.ConnectionError:
                st.error("Impossible de joindre l'API. Vérifiez que le backend est démarré.")
                st.stop()
            except requests.exceptions.HTTPError as e:
                st.error(f"Erreur API ({e.response.status_code}) : {e.response.text}")
                st.stop()

# ---------------------------------------------------------------------------
# Display result
# ---------------------------------------------------------------------------

if "last_generated" in st.session_state:
    data = st.session_state["last_generated"]

    st.divider()
    st.subheader("📝 Prompt Généré")

    st.text_area("Prompt principal", value=data["prompt"], height=150, key="main_prompt_display")

    score = data.get("score", 0)
    score_color = "green" if score >= 75 else "orange" if score >= 50 else "red"
    st.markdown(f"**Score qualité :** :{score_color}[{score}/100]")
    st.progress(int(score) / 100)

    with st.expander("💡 Explication des choix structurels"):
        st.write(data.get("explanation", "—"))

    with st.expander("🔀 Variantes alternatives"):
        for i, variant in enumerate(data.get("variants", []), 1):
            st.markdown(f"**Variante {i}**")
            st.text_area(f"variant_{i}", value=variant, height=100, label_visibility="collapsed")

    st.divider()
    col_save, col_opt, col_exp = st.columns(3)

    # Save to library
    with col_save:
        with st.popover("💾 Sauvegarder"):
            save_title = st.text_input("Titre", value="Mon prompt audio")
            save_tags = st.text_input("Tags (séparés par des virgules)", value="")
            if st.button("Confirmer la sauvegarde"):
                tags = [t.strip() for t in save_tags.split(",") if t.strip()]
                try:
                    r = requests.post(
                        f"{API_BASE}/api/library",
                        json={
                            "title": save_title,
                            "content": data["prompt"],
                            "type": audio_type,
                            "tags": tags,
                            "score": data.get("score"),
                        },
                        timeout=10,
                    )
                    r.raise_for_status()
                    st.success("Prompt sauvegardé ✓")
                except Exception as e:
                    st.error(f"Erreur : {e}")

    # Optimise
    with col_opt:
        with st.popover("🔄 Optimiser"):
            objective = st.selectbox("Objectif", ["clarity", "precision", "creativity", "technical"])
            if st.button("Lancer l'optimisation"):
                with st.spinner("Optimisation…"):
                    try:
                        r = requests.post(
                            f"{API_BASE}/api/optimize",
                            json={"raw_prompt": data["prompt"], "objective": objective, "type": audio_type},
                            timeout=30,
                        )
                        r.raise_for_status()
                        opt = r.json()
                        st.session_state["last_generated"]["prompt"] = opt["optimized_prompt"]
                        st.success(
                            f"Score : {opt['score_before']} → {opt['score_after']}"
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {e}")

    # Export
    with col_exp:
        with st.popover("📤 Exporter"):
            fmt = st.selectbox("Format", ["json", "markdown"])
            if st.button("Télécharger"):
                # Build the export payload locally — no need to save to library first
                from datetime import datetime, timezone
                import json as _json

                prompt_content = data["prompt"]
                if fmt == "json":
                    payload = {
                        "export_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                        "prompts": [
                            {
                                "id": None,
                                "title": "Prompt généré",
                                "content": prompt_content,
                                "type": audio_type,
                                "score": data.get("score"),
                                "tags": [],
                                "created_at": datetime.now(timezone.utc).isoformat(),
                            }
                        ],
                    }
                    file_bytes = _json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
                    mime = "application/json"
                    ext = "json"
                else:
                    today = datetime.now(timezone.utc).strftime("%d %B %Y")
                    score_str = f"{data['score']}/100" if data.get("score") is not None else "N/A"
                    md = (
                        f"# Bibliothèque de Prompts Audio\n"
                        f"**Exporté le** : {today}\n\n---\n\n"
                        f"## Prompt généré\n"
                        f"**Type** : {audio_type} | **Score** : {score_str} | **Tags** : \n\n"
                        f"{prompt_content}\n"
                    )
                    file_bytes = md.encode("utf-8")
                    mime = "text/markdown"
                    ext = "md"

                st.download_button(
                    label=f"📥 Télécharger .{ext}",
                    data=file_bytes,
                    file_name=f"prompt_export.{ext}",
                    mime=mime,
                )

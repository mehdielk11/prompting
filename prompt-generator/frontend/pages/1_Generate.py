"""Page 1 — Generate a professional audio prompt."""

from __future__ import annotations

import json as _json
from datetime import datetime, timezone

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

# Persist audio_type across reruns so popovers can read it after form submission
if submitted:
    st.session_state["audio_type"] = audio_type

_audio_type: str = st.session_state.get("audio_type", "tts")

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
                        "type": _audio_type,
                        "tone": tone,
                        "duration": duration,
                    },
                    timeout=60,
                )
                resp.raise_for_status()
                data = resp.json()
                st.session_state["last_generated"] = data
                # Clear any pending optimize trigger from a previous run
                st.session_state.pop("_run_optimize", None)
            except requests.exceptions.ConnectionError:
                st.error("Impossible de joindre l'API. Vérifiez que le backend est démarré.")
                st.stop()
            except requests.exceptions.HTTPError as e:
                st.error(f"Erreur API ({e.response.status_code}) : {e.response.text}")
                st.stop()

# ---------------------------------------------------------------------------
# Optimization — executed at top-level scope (never inside a popover/spinner)
# ---------------------------------------------------------------------------

if st.session_state.get("_run_optimize"):
    _obj = st.session_state.pop("_run_optimize")
    _prompt = st.session_state.get("last_generated", {}).get("prompt", "")
    if _prompt:
        with st.spinner("Optimisation en cours…"):
            try:
                r = requests.post(
                    f"{API_BASE}/api/optimize",
                    json={"raw_prompt": _prompt, "objective": _obj, "type": _audio_type},
                    timeout=60,
                )
                r.raise_for_status()
                opt = r.json()
                st.session_state["last_generated"]["prompt"] = opt["optimized_prompt"]
                st.session_state["last_generated"]["score"] = opt["score_after"]
                st.session_state["_optimize_result"] = opt
            except requests.exceptions.HTTPError as e:
                st.session_state["_optimize_error"] = f"Erreur API ({e.response.status_code}) : {e.response.text}"
            except Exception as e:
                st.session_state["_optimize_error"] = str(e)

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

    # Show optimize feedback inline (above the buttons)
    if "_optimize_result" in st.session_state:
        opt_res = st.session_state.pop("_optimize_result")
        delta = opt_res["score_after"] - opt_res["score_before"]
        delta_str = f"+{delta:.1f}" if delta >= 0 else f"{delta:.1f}"
        color = "green" if delta > 0 else "orange" if delta == 0 else "red"
        st.success(
            f"✅ Prompt optimisé — Score : **{opt_res['score_before']}** → "
            f"**:{color}[{opt_res['score_after']}]** ({delta_str})"
        )

        # Dimension breakdown
        db = opt_res.get("dimensions_before")
        da = opt_res.get("dimensions_after")
        if db and da:
            with st.expander("📊 Détail des dimensions avant / après"):
                dim_labels = {
                    "clarity": "Clarté",
                    "specificity": "Spécificité",
                    "structure": "Structure",
                    "relevance": "Pertinence",
                    "creativity": "Créativité",
                }
                cols = st.columns(5)
                for i, (key, label) in enumerate(dim_labels.items()):
                    before_val = db[key] if isinstance(db, dict) else getattr(db, key)
                    after_val = da[key] if isinstance(da, dict) else getattr(da, key)
                    d = after_val - before_val
                    cols[i].metric(label, f"{after_val:.0f}", f"{d:+.0f}")

        if opt_res.get("changes"):
            with st.expander("📋 Modifications apportées"):
                for change in opt_res["changes"]:
                    st.markdown(f"- {change}")

    if "_optimize_error" in st.session_state:
        st.error(st.session_state.pop("_optimize_error"))

    col_save, col_opt, col_exp = st.columns(3)

    # --- Save to library ---
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
                            "type": _audio_type,
                            "tags": tags,
                            "score": data.get("score"),
                        },
                        timeout=10,
                    )
                    r.raise_for_status()
                    st.success("Prompt sauvegardé ✓")
                except Exception as e:
                    st.error(f"Erreur : {e}")

    # --- Optimise ---
    with col_opt:
        with st.popover("🔄 Optimiser"):
            objective = st.selectbox(
                "Objectif",
                ["clarity", "precision", "creativity", "technical"],
                key="opt_objective",
            )
            if st.button("Lancer l'optimisation", key="btn_optimize"):
                # Store the trigger in session_state — actual API call runs at top-level on next rerun
                st.session_state["_run_optimize"] = objective
                st.rerun()

    # --- Export ---
    with col_exp:
        with st.popover("📤 Exporter"):
            fmt = st.selectbox("Format", ["json", "markdown"], key="export_fmt")

            # Build file content eagerly so download_button triggers instantly
            prompt_content = data["prompt"]
            if fmt == "json":
                payload = {
                    "export_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    "prompts": [
                        {
                            "id": None,
                            "title": "Prompt généré",
                            "content": prompt_content,
                            "type": _audio_type,
                            "score": data.get("score"),
                            "tags": [],
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        }
                    ],
                }
                file_bytes = _json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
                mime = "application/json"
                filename = "prompt_export.json"
            else:
                today = datetime.now(timezone.utc).strftime("%d %B %Y")
                score_str = f"{data['score']}/100" if data.get("score") is not None else "N/A"
                md = (
                    f"# Bibliothèque de Prompts Audio\n"
                    f"**Exporté le** : {today}\n\n---\n\n"
                    f"## Prompt généré\n"
                    f"**Type** : {_audio_type} | **Score** : {score_str} | **Tags** : \n\n"
                    f"{prompt_content}\n"
                )
                file_bytes = md.encode("utf-8")
                mime = "text/markdown"
                filename = "prompt_export.md"

            st.download_button(
                label="📥 Télécharger",
                data=file_bytes,
                file_name=filename,
                mime=mime,
                key="dl_export",
                use_container_width=True,
            )

    st.divider()

    with st.expander("💡 Explication des choix structurels"):
        st.write(data.get("explanation", "—"))

    with st.expander("🔀 Variantes alternatives"):
        for i, variant in enumerate(data.get("variants", []), 1):
            st.markdown(f"**Variante {i}**")
            st.text_area(f"variant_{i}", value=variant, height=100, label_visibility="collapsed")


"""Page 2 — Prompt library with search, filters, and bulk export."""

from __future__ import annotations

import requests
import streamlit as st

API_BASE = st.session_state.get("api_base", "http://localhost:8000")

st.set_page_config(page_title="Bibliothèque", page_icon="📚", layout="wide")
st.title("📚 Bibliothèque de Prompts")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def fetch_prompts(query: str = "", page: int = 1, type_filter: str = "", min_score: float | None = None) -> dict:
    """Fetch prompts from the API (search or list)."""
    try:
        if query:
            resp = requests.get(
                f"{API_BASE}/api/library/search",
                params={"q": query, "page": page, "page_size": 12},
                timeout=10,
            )
        else:
            params: dict = {"page": page, "page_size": 12}
            if type_filter:
                params["type"] = type_filter
            if min_score is not None:
                params["min_score"] = min_score
            resp = requests.get(f"{API_BASE}/api/library", params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        st.error("Impossible de joindre l'API.")
        return {"items": [], "total": 0, "page": 1, "page_size": 12}
    except Exception as e:
        st.error(f"Erreur : {e}")
        return {"items": [], "total": 0, "page": 1, "page_size": 12}


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

col_search, col_type, col_score = st.columns([3, 1, 1])
with col_search:
    search_query = st.text_input("🔍 Rechercher", placeholder="Titre ou contenu…")
with col_type:
    type_filter = st.selectbox("Type", ["", "tts", "music", "sfx", "voiceover"], format_func=lambda x: x or "Tous")
with col_score:
    min_score = st.number_input("Score min", min_value=0, max_value=100, value=0, step=5)

if "lib_page" not in st.session_state:
    st.session_state["lib_page"] = 1

data = fetch_prompts(
    query=search_query,
    page=st.session_state["lib_page"],
    type_filter=type_filter,
    min_score=min_score if min_score > 0 else None,
)

items = data.get("items", [])
total = data.get("total", 0)
page_size = data.get("page_size", 12)
total_pages = max(1, -(-total // page_size))  # ceiling division

st.caption(f"{total} prompt(s) trouvé(s)")

# ---------------------------------------------------------------------------
# Bulk export selection
# ---------------------------------------------------------------------------

if "selected_ids" not in st.session_state:
    st.session_state["selected_ids"] = set()

if items:
    with st.expander("📤 Export en masse"):
        col_sel, col_fmt, col_btn = st.columns([2, 1, 1])
        with col_sel:
            st.write(f"{len(st.session_state['selected_ids'])} prompt(s) sélectionné(s)")
        with col_fmt:
            bulk_fmt = st.selectbox("Format", ["json", "markdown"], key="bulk_fmt")
        with col_btn:
            if st.button("Exporter la sélection") and st.session_state["selected_ids"]:
                try:
                    r = requests.post(
                        f"{API_BASE}/api/export",
                        json={"ids": list(st.session_state["selected_ids"]), "format": bulk_fmt},
                        timeout=15,
                    )
                    r.raise_for_status()
                    ext = "json" if bulk_fmt == "json" else "md"
                    st.download_button(
                        label=f"📥 Télécharger .{ext}",
                        data=r.content,
                        file_name=f"bulk_export.{ext}",
                    )
                except Exception as e:
                    st.error(f"Erreur export : {e}")

# ---------------------------------------------------------------------------
# Prompt cards grid
# ---------------------------------------------------------------------------

if not items:
    st.info("Aucun prompt trouvé. Générez-en un depuis la page Générer !")
else:
    cols = st.columns(3)
    for idx, prompt in enumerate(items):
        with cols[idx % 3]:
            score = prompt.get("score")
            score_badge = f"🟢 {score:.0f}/100" if score and score >= 75 else (
                f"🟡 {score:.0f}/100" if score and score >= 50 else (
                    f"🔴 {score:.0f}/100" if score else "⚪ N/A"
                )
            )
            tags_str = " ".join(f"`{t}`" for t in prompt.get("tags", []))

            with st.container(border=True):
                # Selection checkbox
                is_selected = st.checkbox(
                    "Sélectionner",
                    key=f"sel_{prompt['id']}",
                    value=prompt["id"] in st.session_state["selected_ids"],
                )
                if is_selected:
                    st.session_state["selected_ids"].add(prompt["id"])
                else:
                    st.session_state["selected_ids"].discard(prompt["id"])

                st.markdown(f"**{prompt['title']}**")
                st.caption(f"{score_badge} · {prompt['type'].upper()} · {tags_str}")
                st.text_area(
                    "Aperçu",
                    value=prompt["content"][:200] + ("…" if len(prompt["content"]) > 200 else ""),
                    height=80,
                    disabled=True,
                    key=f"preview_{prompt['id']}",
                    label_visibility="collapsed",
                )

                btn_col1, btn_col2, btn_col3 = st.columns(3)

                # Duplicate
                with btn_col1:
                    if st.button("📋", key=f"dup_{prompt['id']}", help="Dupliquer"):
                        try:
                            r = requests.post(f"{API_BASE}/api/library/{prompt['id']}/duplicate", timeout=10)
                            r.raise_for_status()
                            st.success("Dupliqué ✓")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

                # Export single
                with btn_col2:
                    if st.button("📤", key=f"exp_{prompt['id']}", help="Exporter"):
                        try:
                            r = requests.post(
                                f"{API_BASE}/api/export",
                                json={"ids": [prompt["id"]], "format": "json"},
                                timeout=10,
                            )
                            r.raise_for_status()
                            st.download_button(
                                "📥",
                                data=r.content,
                                file_name=f"prompt_{prompt['id']}.json",
                                key=f"dl_{prompt['id']}",
                            )
                        except Exception as e:
                            st.error(str(e))

                # Delete
                with btn_col3:
                    if st.button("🗑️", key=f"del_{prompt['id']}", help="Supprimer"):
                        try:
                            r = requests.delete(f"{API_BASE}/api/library/{prompt['id']}", timeout=10)
                            r.raise_for_status()
                            st.success("Supprimé ✓")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

st.divider()
pcol1, pcol2, pcol3 = st.columns([1, 2, 1])
with pcol1:
    if st.button("← Précédent") and st.session_state["lib_page"] > 1:
        st.session_state["lib_page"] -= 1
        st.rerun()
with pcol2:
    st.caption(f"Page {st.session_state['lib_page']} / {total_pages}")
with pcol3:
    if st.button("Suivant →") and st.session_state["lib_page"] < total_pages:
        st.session_state["lib_page"] += 1
        st.rerun()

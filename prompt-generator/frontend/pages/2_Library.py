"""Page 2 — Prompt library with search, filters, and bulk export."""

from __future__ import annotations

import json as _json
from datetime import datetime, timezone

import requests
import streamlit as st

API_BASE = st.session_state.get("api_base", "http://localhost:8000")

st.set_page_config(page_title="Bibliothèque", page_icon="📚", layout="wide")
st.title("📚 Bibliothèque de Prompts")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def fetch_prompts(
    query: str = "",
    page: int = 1,
    type_filter: str = "",
    min_score: float | None = None,
) -> dict:
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


def _build_json_bytes(prompt: dict) -> bytes:
    """Serialize a single prompt to the standard JSON export format."""
    payload = {
        "export_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "prompts": [
            {
                "id": prompt["id"],
                "title": prompt["title"],
                "content": prompt["content"],
                "type": prompt["type"],
                "score": prompt.get("score"),
                "tags": prompt.get("tags", []),
                "created_at": prompt.get("created_at"),
            }
        ],
    }
    return _json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def _build_bulk_json_bytes(ids: list[int]) -> bytes | None:
    """Fetch and serialize multiple prompts to JSON export format."""
    try:
        r = requests.post(
            f"{API_BASE}/api/export",
            json={"ids": ids, "format": "json"},
            timeout=15,
        )
        r.raise_for_status()
        return r.content
    except Exception:
        return None


def _build_bulk_md_bytes(ids: list[int]) -> bytes | None:
    """Fetch and serialize multiple prompts to Markdown export format."""
    try:
        r = requests.post(
            f"{API_BASE}/api/export",
            json={"ids": ids, "format": "markdown"},
            timeout=15,
        )
        r.raise_for_status()
        return r.content
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

col_search, col_type, col_score = st.columns([3, 1, 1])
with col_search:
    search_query = st.text_input("🔍 Rechercher", placeholder="Titre ou contenu…")
with col_type:
    type_filter = st.selectbox(
        "Type",
        ["", "tts", "music", "sfx", "voiceover"],
        format_func=lambda x: x or "Tous",
    )
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
total_pages = max(1, -(-total // page_size))

st.caption(f"{total} prompt(s) trouvé(s)")

# ---------------------------------------------------------------------------
# Bulk export — download button rendered eagerly, no intermediate click
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
            selected = list(st.session_state["selected_ids"])
            if selected:
                # Build bytes eagerly so download_button triggers instantly
                if bulk_fmt == "json":
                    bulk_bytes = _build_bulk_json_bytes(selected)
                    bulk_mime = "application/json"
                    bulk_ext = "json"
                else:
                    bulk_bytes = _build_bulk_md_bytes(selected)
                    bulk_mime = "text/markdown"
                    bulk_ext = "md"

                if bulk_bytes:
                    st.download_button(
                        label=f"📥 Télécharger .{bulk_ext}",
                        data=bulk_bytes,
                        file_name=f"bulk_export.{bulk_ext}",
                        mime=bulk_mime,
                        key="bulk_dl",
                    )
                else:
                    st.error("Erreur lors de la préparation de l'export.")
            else:
                st.button("📥 Télécharger", disabled=True, key="bulk_dl_disabled")

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
            score_badge = (
                f"🟢 {score:.0f}/100" if score and score >= 75
                else f"🟡 {score:.0f}/100" if score and score >= 50
                else f"🔴 {score:.0f}/100" if score
                else "⚪ N/A"
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
                            r = requests.post(
                                f"{API_BASE}/api/library/{prompt['id']}/duplicate",
                                timeout=10,
                            )
                            r.raise_for_status()
                            st.success("Dupliqué ✓")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

                # Export single — download button rendered directly, no intermediate click
                with btn_col2:
                    export_bytes = _build_json_bytes(prompt)
                    st.download_button(
                        label="📤",
                        data=export_bytes,
                        file_name=f"prompt_{prompt['id']}.json",
                        mime="application/json",
                        key=f"dl_{prompt['id']}",
                        help="Exporter en JSON",
                    )

                # Delete
                with btn_col3:
                    if st.button("🗑️", key=f"del_{prompt['id']}", help="Supprimer"):
                        try:
                            r = requests.delete(
                                f"{API_BASE}/api/library/{prompt['id']}",
                                timeout=10,
                            )
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

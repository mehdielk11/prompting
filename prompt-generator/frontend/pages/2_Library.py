"""Page 2 — Prompt library with search, filters, and bulk export."""

from __future__ import annotations

import json as _json
from datetime import datetime, timezone

import requests
import streamlit as st

from frontend.theme import (
    inject_theme,
    gradient_text,
    hero_section,
    gradient_divider,
    prompt_display,
    score_ring,
    type_badge,
    tag_badge,
    render_sidebar,
)

API_BASE = st.session_state.get("api_base", "http://localhost:8000")

st.set_page_config(page_title="Bibliothèque", page_icon="📚", layout="wide")

# Inject the complete CSS theme
inject_theme()

# ---------------------------------------------------------------------------
# Sidebar branding
# ---------------------------------------------------------------------------
render_sidebar()

# ---------------------------------------------------------------------------
# Hero section
# ---------------------------------------------------------------------------
st.markdown(
    hero_section(
        title_html=f"Bibliothèque de {gradient_text('prompts')}",
        subtitle="Recherchez, filtrez, dupliquez ou exportez vos prompts audio sauvegardés en masse."
    ),
    unsafe_allow_html=True,
)


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


def _prompt_to_json_bytes(prompt: dict) -> bytes:
    """Serialize a single prompt dict to JSON export bytes — no API call needed."""
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


@st.cache_data(ttl=10, show_spinner=False)
def _fetch_bulk_export(ids_tuple: tuple[int, ...], fmt: str) -> bytes | None:
    """Fetch bulk export bytes from the API, cached to avoid re-fetching on every render."""
    try:
        r = requests.post(
            f"{API_BASE}/api/export",
            json={"ids": list(ids_tuple), "format": fmt},
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
# Bulk export
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
            selected = sorted(st.session_state["selected_ids"])
            if selected:
                bulk_bytes = _fetch_bulk_export(tuple(selected), bulk_fmt)
                if bulk_bytes:
                    ext = "json" if bulk_fmt == "json" else "md"
                    mime = "application/json" if bulk_fmt == "json" else "text/markdown"
                    st.download_button(
                        label=f"📥 Télécharger .{ext}",
                        data=bulk_bytes,
                        file_name=f"bulk_export.{ext}",
                        mime=mime,
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
        pid = prompt["id"]
        with cols[idx % 3]:
            score = prompt.get("score")
            with st.container(border=True):
                # Header row: Flex layout with Title and Score Ring
                st.markdown(
                    f'<div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px; margin-bottom:8px">'
                    f'<div style="font-weight:700; font-size:1.05rem; color:var(--text); line-height:1.2; word-break:break-word">{prompt["title"]}</div>'
                    f'<div>{score_ring(score, size=42) if score is not None else ""}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

                # Badges for type and tags
                badges_html = type_badge(prompt["type"]) + " " + " ".join(tag_badge(t) for t in prompt.get("tags", []))
                st.markdown(f'<div style="margin-bottom:12px; display:flex; flex-wrap:wrap; gap:4px">{badges_html}</div>', unsafe_allow_html=True)

                # Code preview block
                preview_text = prompt["content"][:160] + ("…" if len(prompt["content"]) > 160 else "")
                st.markdown(prompt_display(preview_text), unsafe_allow_html=True)
                st.markdown('<div style="margin-top:12px"></div>', unsafe_allow_html=True)

                # Selection checkbox (styled toggles)
                is_selected = st.checkbox(
                    "Sélectionner pour export",
                    key=f"sel_{pid}",
                    value=pid in st.session_state["selected_ids"],
                )
                if is_selected:
                    st.session_state["selected_ids"].add(pid)
                else:
                    st.session_state["selected_ids"].discard(pid)

                btn_col1, btn_col2, btn_col3 = st.columns(3)

                # Duplicate — API call + rerun in one shot
                with btn_col1:
                    if st.button("📋", key=f"dup_{pid}", help="Dupliquer", use_container_width=True):
                        try:
                            r = requests.post(
                                f"{API_BASE}/api/library/{pid}/duplicate",
                                timeout=10,
                            )
                            r.raise_for_status()
                        except Exception as e:
                            st.error(str(e))
                        st.rerun()

                # Export — local serialisation, no API call, no rerun
                with btn_col2:
                    st.download_button(
                        label="📤",
                        data=_prompt_to_json_bytes(prompt),
                        file_name=f"prompt_{pid}.json",
                        mime="application/json",
                        key=f"dl_{pid}",
                        help="Exporter en JSON",
                        use_container_width=True,
                    )

                # Delete — API call + rerun in one shot
                with btn_col3:
                    if st.button("🗑️", key=f"del_{pid}", help="Supprimer", use_container_width=True):
                        try:
                            r = requests.delete(
                                f"{API_BASE}/api/library/{pid}",
                                timeout=10,
                            )
                            r.raise_for_status()
                        except Exception as e:
                            st.error(str(e))
                        st.rerun()

# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

st.markdown(gradient_divider(), unsafe_allow_html=True)
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

"""Library page — search, filter, and manage saved prompts."""

from __future__ import annotations

import json as _json
from datetime import datetime, timezone

import requests
import streamlit as st

from frontend.theme import (
    gradient_divider,
    gradient_text,
    hero_section,
    prompt_display,
    score_ring,
    tag_badge,
    type_badge,
    loading_skeleton_grid,
)

API_BASE = st.session_state.get("api_base", "http://localhost:8000")

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


# Safe import for fragment
if hasattr(st, "fragment"):
    fragment_decorator = st.fragment
else:
    fragment_decorator = st.experimental_fragment


@fragment_decorator
def library_content_fragment():
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

    # Active query configuration for caching
    active_key = (search_query, type_filter, min_score, st.session_state["lib_page"])
    
    # Check if we need to fetch prompts
    should_fetch = (
        "active_query_key" not in st.session_state
        or st.session_state["active_query_key"] != active_key
        or "cached_prompts" not in st.session_state
        or st.session_state["cached_prompts"] is None
    )

    if should_fetch:
        grid_placeholder = st.empty()
        with grid_placeholder.container():
            st.markdown(loading_skeleton_grid(count=6), unsafe_allow_html=True)
        
        # API call with minor buffer delay for premium visual shimmer transition
        import time
        start_time = time.time()
        
        data = fetch_prompts(
            query=search_query,
            page=st.session_state["lib_page"],
            type_filter=type_filter,
            min_score=min_score if min_score > 0 else None,
        )
        
        elapsed = time.time() - start_time
        if elapsed < 0.25:
            time.sleep(0.25 - elapsed)
            
        st.session_state["cached_prompts"] = data
        st.session_state["active_query_key"] = active_key
        grid_placeholder.empty()
    else:
        data = st.session_state["cached_prompts"]

    items = data.get("items", [])
    total = data.get("total", 0)
    page_size = data.get("page_size", 12)
    total_pages = max(1, -(-total // page_size))

    # Trigger pending duplicate action if requested in optimistic flow
    pending_dup_id = st.session_state.get("pending_duplicate_source_id")
    if pending_dup_id:
        try:
            r = requests.post(f"{API_BASE}/api/library/{pending_dup_id}/duplicate", timeout=10)
            r.raise_for_status()
            new_prompt = r.json()
            
            # Swap placeholder with real prompt
            p_id = f"temp_dup_{pending_dup_id}"
            items_list = st.session_state["cached_prompts"]["items"]
            p_idx = next((i for i, x in enumerate(items_list) if x["id"] == p_id), None)
            if p_idx is not None:
                items_list[p_idx] = new_prompt
                st.toast("✅ Prompt dupliqué avec succès !")
        except Exception as e:
            # Cleanup placeholder on error
            p_id = f"temp_dup_{pending_dup_id}"
            st.session_state["cached_prompts"]["items"] = [x for x in st.session_state["cached_prompts"]["items"] if x["id"] != p_id]
            st.session_state["cached_prompts"]["total"] -= 1
            st.error(f"Erreur lors de la duplication : {e}")
        finally:
            st.session_state.pop("pending_duplicate_source_id", None)
        st.rerun()

    if "selected_ids" not in st.session_state:
        st.session_state["selected_ids"] = set()

    # Toolbar row: result count on the left, export button on the right
    count_col, fmt_col, export_col = st.columns([3, 1, 1])
    with count_col:
        st.caption(f"{total} prompt(s) trouvé(s)")

    if items:
        with fmt_col:
            bulk_fmt = st.selectbox(
                "Format d'export",
                ["json", "markdown"],
                key="bulk_fmt",
                label_visibility="collapsed",
            )
        with export_col:
            selected = sorted(st.session_state["selected_ids"])
            n = len(selected)
            export_key = (tuple(selected), bulk_fmt)

            if not selected:
                # Clear stale cached bytes when nothing is selected
                st.session_state.pop("_export_bytes", None)
                st.session_state.pop("_export_key", None)
                st.button(
                    "📤 Exporter",
                    disabled=True,
                    key="bulk_dl_disabled",
                    use_container_width=True,
                    help="Sélectionnez des prompts pour les exporter",
                )
            elif (
                st.session_state.get("_export_key") == export_key
                and st.session_state.get("_export_bytes")
            ):
                # Bytes already prepared for this exact selection+format → download
                ext = "json" if bulk_fmt == "json" else "md"
                mime = "application/json" if bulk_fmt == "json" else "text/markdown"
                st.download_button(
                    label=f"📥 Télécharger ({n})",
                    data=st.session_state["_export_bytes"],
                    file_name=f"export.{ext}",
                    mime=mime,
                    key="bulk_dl",
                    use_container_width=True,
                )
            else:
                # Selection changed or first time — fetch only on explicit click
                if st.button(
                    f"📤 Exporter ({n})",
                    key="bulk_prepare",
                    use_container_width=True,
                ):
                    bulk_bytes = _fetch_bulk_export(tuple(selected), bulk_fmt)
                    if bulk_bytes:
                        st.session_state["_export_key"] = export_key
                        st.session_state["_export_bytes"] = bulk_bytes
                        st.rerun()
                    else:
                        st.error("Erreur lors de la préparation de l'export.")

    # ---------------------------------------------------------------------------
    # Prompt cards grid
    # ---------------------------------------------------------------------------
    if not items:
        st.info("Aucun prompt trouvé. Générez-en un depuis la page Générer !")
    else:
        cols = st.columns(3)
        for idx, prompt in enumerate(items):
            pid = prompt["id"]
            is_temp = str(pid).startswith("temp_")
            with cols[idx % 3]:
                score = prompt.get("score")

                card_style = ""
                if prompt.get("is_placeholder"):
                    card_style = "pulsing-glow"
                elif prompt.get("is_deleting"):
                    card_style = "fade-out"

                with st.container(border=True):
                    # Optimistic UI overlay
                    if card_style:
                        st.markdown(
                            f'<div class="{card_style}" style="position:absolute;top:0;left:0;right:0;bottom:0;border-radius:16px;pointer-events:none;border:1.5px solid var(--primary);"></div>',
                            unsafe_allow_html=True,
                        )
                        if prompt.get("is_placeholder"):
                            st.markdown(
                                '<div style="color:var(--primary);font-size:0.72rem;font-weight:700;margin-bottom:8px;display:flex;align-items:center;gap:6px;">'
                                '<span class="pulsing-glow" style="width:8px;height:8px;background:var(--primary);border-radius:50%"></span>'
                                'DUPLICATION EN COURS...</div>',
                                unsafe_allow_html=True,
                            )

                    # ── Card header: title + score ring ──────────────────
                    st.markdown(
                        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:10px">'
                        f'<div style="font-weight:700;font-size:1rem;color:var(--text);line-height:1.25;word-break:break-word">{prompt["title"]}</div>'
                        f'<div style="flex-shrink:0">{score_ring(score, size=42) if score is not None else ""}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                    # ── Type + tag badges ─────────────────────────────────
                    badges_html = type_badge(prompt["type"]) + " " + " ".join(
                        tag_badge(t) for t in prompt.get("tags", [])
                    )
                    st.markdown(
                        f'<div style="margin-bottom:12px;display:flex;flex-wrap:wrap;gap:4px">{badges_html}</div>',
                        unsafe_allow_html=True,
                    )

                    # ── Content preview ───────────────────────────────────
                    preview_text = prompt["content"][:160] + ("…" if len(prompt["content"]) > 160 else "")
                    st.markdown(prompt_display(preview_text), unsafe_allow_html=True)

                    # ── Card footer ───────────────────────────────────────
                    st.markdown('<div class="card-footer" style="flex-direction: column; align-items: stretch; gap: 8px; display: flex;">', unsafe_allow_html=True)

                    is_selected = pid in st.session_state["selected_ids"]
                    sel_label = "Sélectionné" if is_selected else "Sélectionner"

                    # Row 1: Selection checkbox spanning full width
                    st.markdown('<div class="lib-card-sel" style="width: 100%;">', unsafe_allow_html=True)
                    toggled = st.checkbox(
                        sel_label,
                        key=f"sel_{pid}",
                        value=is_selected,
                        disabled=is_temp,
                    )
                    if toggled:
                        st.session_state["selected_ids"].add(pid)
                    else:
                        st.session_state["selected_ids"].discard(pid)
                    st.markdown('</div>', unsafe_allow_html=True)

                    # Row 2: Action buttons row spanning full width
                    st.markdown('<div class="lib-card-actions" style="width: 100%;">', unsafe_allow_html=True)
                    a1, a2, a3 = st.columns([1, 1, 1], gap="small")

                    # Duplicate
                    with a1:
                        if st.button(
                            "⎘  Dupliquer",
                            key=f"dup_{pid}",
                            help="Dupliquer ce prompt",
                            use_container_width=True,
                            disabled=is_temp,
                        ):
                            placeholder_id = f"temp_dup_{pid}"
                            placeholder_prompt = {
                                "id": placeholder_id,
                                "title": f"{prompt['title']} (Copie)",
                                "content": "Duplication en cours...",
                                "type": prompt["type"],
                                "tags": prompt.get("tags", []) + ["copie"],
                                "score": prompt.get("score"),
                                "is_placeholder": True,
                            }
                            idx_to_insert = next(
                                (i for i, x in enumerate(st.session_state["cached_prompts"]["items"]) if x["id"] == pid), 0
                            )
                            st.session_state["cached_prompts"]["items"].insert(idx_to_insert + 1, placeholder_prompt)
                            st.session_state["cached_prompts"]["total"] += 1
                            st.session_state["pending_duplicate_source_id"] = pid
                            st.toast("Duplication en cours…")
                            st.rerun()

                    # Export single
                    with a2:
                        st.download_button(
                            label="↓  Export",
                            data=_prompt_to_json_bytes(prompt),
                            file_name=f"prompt_{pid}.json",
                            mime="application/json",
                            key=f"dl_{pid}",
                            help="Exporter ce prompt en JSON",
                            use_container_width=True,
                            disabled=is_temp,
                            on_click=lambda: st.toast("Prompt exporté !"),
                        )

                    # Delete with confirmation popover
                    with a3:
                        with st.popover(
                            "🗑️",
                            help="Supprimer ce prompt",
                            use_container_width=True,
                            disabled=is_temp,
                            key=f"pop_del_{pid}",
                        ):
                            st.markdown(
                                '<p style="font-size:0.85rem;color:var(--text);margin:0 0 12px 0;font-weight:600">'
                                "Supprimer ce prompt ?</p>"
                                '<p style="font-size:0.75rem;color:var(--text-sec);margin:0 0 14px 0">'
                                "Cette action est irréversible.</p>",
                                unsafe_allow_html=True,
                            )
                            if st.button(
                                "Confirmer la suppression",
                                key=f"conf_del_{pid}",
                                type="primary",
                                use_container_width=True,
                            ):
                                item_idx = next(
                                    (i for i, x in enumerate(st.session_state["cached_prompts"]["items"]) if x["id"] == pid),
                                    None,
                                )
                                if item_idx is not None:
                                    item_to_delete = st.session_state["cached_prompts"]["items"][item_idx]
                                    st.session_state["cached_prompts"]["items"][item_idx]["is_deleting"] = True
                                    st.toast("Suppression en cours…")
                                    st.session_state["cached_prompts"]["items"].pop(item_idx)
                                    st.session_state["cached_prompts"]["total"] -= 1
                                    try:
                                        r = requests.delete(f"{API_BASE}/api/library/{pid}", timeout=10)
                                        r.raise_for_status()
                                        st.toast("✅ Prompt supprimé !")
                                    except Exception as e:
                                        st.session_state["cached_prompts"]["items"].insert(item_idx, item_to_delete)
                                        st.session_state["cached_prompts"]["total"] += 1
                                        st.error(f"Erreur : {e}")
                                    st.rerun()

                    st.markdown('</div></div>', unsafe_allow_html=True)

    # ---------------------------------------------------------------------------
    # Pagination — centered pill bar
    # ---------------------------------------------------------------------------
    st.markdown(gradient_divider(), unsafe_allow_html=True)
    st.markdown('<div class="lib-pagination">', unsafe_allow_html=True)
    pcol1, pcol2, pcol3 = st.columns([1, 2, 1])
    with pcol1:
        prev_disabled = st.session_state["lib_page"] <= 1
        if st.button(
            "← Précédent",
            disabled=prev_disabled,
            use_container_width=True,
            key="lib_prev",
        ):
            st.session_state["lib_page"] -= 1
            st.rerun()
    with pcol2:
        st.markdown(
            f'<div style="text-align:center;color:var(--text-sec);font-size:0.8rem;padding-top:8px">'
            f'Page <strong style="color:var(--text)">{st.session_state["lib_page"]}</strong> / {total_pages}'
            f'</div>',
            unsafe_allow_html=True,
        )
    with pcol3:
        next_disabled = st.session_state["lib_page"] >= total_pages
        if st.button(
            "Suivant →",
            disabled=next_disabled,
            use_container_width=True,
            key="lib_next",
        ):
            st.session_state["lib_page"] += 1
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


# Render fragment
library_content_fragment()

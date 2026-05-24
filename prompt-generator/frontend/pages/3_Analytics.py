"""Page 3 — Analytics dashboard."""

from __future__ import annotations

import requests
import streamlit as st

API_BASE = st.session_state.get("api_base", "http://localhost:8000")

st.set_page_config(page_title="Analytics", page_icon="📊", layout="wide")
st.title("📊 Analytics")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


@st.cache_data(ttl=30)
def load_all_prompts(api_base: str) -> list[dict]:
    """Fetch all prompts (up to 1000) for analytics."""
    try:
        resp = requests.get(f"{api_base}/api/library", params={"page": 1, "page_size": 1000}, timeout=15)
        resp.raise_for_status()
        return resp.json().get("items", [])
    except Exception:
        return []


prompts = load_all_prompts(API_BASE)

if not prompts:
    st.info("Aucune donnée disponible. Générez et sauvegardez des prompts pour voir les analytics.")
    st.stop()

# ---------------------------------------------------------------------------
# KPI row
# ---------------------------------------------------------------------------

scored = [p for p in prompts if p.get("score") is not None]
avg_score = round(sum(p["score"] for p in scored) / len(scored), 1) if scored else 0

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Total prompts", len(prompts))
kpi2.metric("Score moyen", f"{avg_score}/100")
kpi3.metric("Prompts scorés", len(scored))
kpi4.metric("Types distincts", len({p["type"] for p in prompts}))

st.divider()

# ---------------------------------------------------------------------------
# Score moyen par type
# ---------------------------------------------------------------------------

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Score moyen par type audio")
    type_scores: dict[str, list[float]] = {}
    for p in scored:
        type_scores.setdefault(p["type"], []).append(p["score"])

    avg_by_type = {t: round(sum(v) / len(v), 1) for t, v in type_scores.items()}

    if avg_by_type:
        # Use st.bar_chart with a simple dict → Series-like structure
        import pandas as pd

        df_type = pd.DataFrame(
            {"Type": list(avg_by_type.keys()), "Score moyen": list(avg_by_type.values())}
        ).set_index("Type")
        st.bar_chart(df_type)
    else:
        st.info("Pas encore de données scorées.")

# ---------------------------------------------------------------------------
# Score distribution histogram
# ---------------------------------------------------------------------------

with col_right:
    st.subheader("Distribution des scores")
    if scored:
        import pandas as pd

        scores = [p["score"] for p in scored]
        bins = list(range(0, 110, 10))
        labels = [f"{b}–{b+10}" for b in bins[:-1]]
        counts = [sum(1 for s in scores if b <= s < b + 10) for b in bins[:-1]]
        df_hist = pd.DataFrame({"Tranche": labels, "Nombre": counts}).set_index("Tranche")
        st.bar_chart(df_hist)
    else:
        st.info("Pas encore de données scorées.")

st.divider()

# ---------------------------------------------------------------------------
# Score evolution over time
# ---------------------------------------------------------------------------

st.subheader("Évolution temporelle des scores")
if scored:
    import pandas as pd

    df_time = pd.DataFrame(
        [{"date": p["created_at"][:10], "score": p["score"]} for p in scored]
    )
    df_time["date"] = pd.to_datetime(df_time["date"])
    df_time = df_time.sort_values("date")
    df_time_grouped = df_time.groupby("date")["score"].mean().reset_index()
    df_time_grouped = df_time_grouped.set_index("date")
    st.line_chart(df_time_grouped)
else:
    st.info("Pas encore de données scorées.")

st.divider()

# ---------------------------------------------------------------------------
# Top 5 prompts
# ---------------------------------------------------------------------------

st.subheader("🏆 Top 5 prompts les mieux notés")
top5 = sorted(scored, key=lambda p: p["score"], reverse=True)[:5]

for rank, p in enumerate(top5, 1):
    with st.container(border=True):
        col_rank, col_info = st.columns([1, 8])
        with col_rank:
            st.markdown(f"### #{rank}")
        with col_info:
            st.markdown(f"**{p['title']}** — `{p['type'].upper()}` — 🟢 {p['score']:.0f}/100")
            st.caption(p["content"][:200] + ("…" if len(p["content"]) > 200 else ""))

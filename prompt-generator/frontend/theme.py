"""Design system — CSS injection and reusable HTML component helpers.

Every page calls ``inject_theme()`` once at the top to apply the dark
glassmorphism design system.  Helper functions return raw HTML strings
that can be rendered with ``st.markdown(..., unsafe_allow_html=True)``.
"""

from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------------------
# Colour tokens (exposed for Python-side logic if needed)
# ---------------------------------------------------------------------------

COLORS = {
    "bg": "#0a0a0f",
    "surface": "#12121a",
    "glass": "rgba(255,255,255,0.04)",
    "glass_border": "rgba(255,255,255,0.08)",
    "glass_hover": "rgba(255,255,255,0.10)",
    "primary": "#6366f1",
    "primary_glow": "rgba(99,102,241,0.35)",
    "secondary": "#06b6d4",
    "success": "#22c55e",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "text": "#f1f5f9",
    "text_secondary": "#94a3b8",
    "text_muted": "#475569",
}

# ---------------------------------------------------------------------------
# CSS — master stylesheet
# ---------------------------------------------------------------------------

_CSS = """
<style>
/* ── Fonts ───────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Root variables ──────────────────────────────────────────────── */
:root {
    --bg:             #0a0a0f;
    --surface:        #12121a;
    --glass:          rgba(255,255,255,0.04);
    --glass-border:   rgba(255,255,255,0.08);
    --glass-hover:    rgba(255,255,255,0.10);
    --primary:        #6366f1;
    --primary-glow:   rgba(99,102,241,0.35);
    --secondary:      #06b6d4;
    --success:        #22c55e;
    --warning:        #f59e0b;
    --danger:         #ef4444;
    --text:           #f1f5f9;
    --text-sec:       #94a3b8;
    --text-muted:     #475569;
    --radius:         16px;
    --radius-sm:      12px;
    --radius-xs:      8px;
    --transition:     all 0.2s ease-out;
    --font:           'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    --mono:           'JetBrains Mono', 'Fira Code', monospace;
}

/* ── Global ──────────────────────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"],
[data-testid="stApp"] {
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: var(--font) !important;
}

/* Background gradient blobs */
[data-testid="stAppViewContainer"]::before {
    content: '';
    position: fixed;
    top: -20%;
    left: -10%;
    width: 600px;
    height: 600px;
    background: radial-gradient(circle, rgba(99,102,241,0.08) 0%, transparent 70%);
    pointer-events: none;
    z-index: 0;
}
[data-testid="stAppViewContainer"]::after {
    content: '';
    position: fixed;
    bottom: -10%;
    right: -10%;
    width: 500px;
    height: 500px;
    background: radial-gradient(circle, rgba(6,182,212,0.06) 0%, transparent 70%);
    pointer-events: none;
    z-index: 0;
}

/* ── Hide Streamlit chrome ───────────────────────────────────────── */
#MainMenu, footer,
[data-testid="stHeaderDecoration"],
[data-testid="stToolbarActions"],
[data-testid="stAppDeployButton"],
[data-testid="stMainMenu"] {
    display: none !important;
}
header[data-testid="stHeader"] {
    background: transparent !important;
    border-bottom: none !important;
    box-shadow: none !important;
    height: 0 !important;
    overflow: visible !important;
}

/* ── Remove blank space above page content caused by hidden header ── */
[data-testid="stMainBlockContainer"],
.main .block-container {
    padding-top: 1.5rem !important;
}

/* ── Sidebar ─────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: rgba(12,12,20,0.85) !important;
    backdrop-filter: blur(20px) !important;
    -webkit-backdrop-filter: blur(20px) !important;
    border-right: 1px solid var(--glass-border) !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    background: transparent !important;
}
/* Hide the stock unstyled Streamlit page list */
[data-testid="stSidebarNav"] {
    display: none !important;
}

/* Premium page link overrides */
section[data-testid="stSidebar"] .stPageLink,
section[data-testid="stSidebar"] a {
    color: var(--text-sec) !important;
    font-family: var(--font) !important;
    font-weight: 500 !important;
    border-radius: var(--radius-xs) !important;
    transition: var(--transition) !important;
    text-decoration: none !important;
    padding: 8px 12px !important;
}
section[data-testid="stSidebar"] .stPageLink:hover,
section[data-testid="stSidebar"] a:hover {
    color: var(--text) !important;
    background: var(--glass-hover) !important;
}
section[data-testid="stSidebar"] .stPageLink[aria-current="page"],
section[data-testid="stSidebar"] a[aria-current="page"] {
    color: var(--primary) !important;
    background: rgba(99,102,241,0.1) !important;
    border-left: 3px solid var(--primary) !important;
}

/* Premium sidebar collapse/expand buttons */
[data-testid="stSidebarCollapseButton"] button {
    background: var(--surface) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: var(--radius-xs) !important;
    color: var(--text) !important;
    transition: var(--transition) !important;
    cursor: pointer !important;
}
[data-testid="stSidebarCollapseButton"] button:hover {
    border-color: var(--primary) !important;
    background: rgba(99,102,241,0.1) !important;
    color: var(--primary) !important;
}

/* Our custom portal expand button (injected by JS into body) */
#ag-sidebar-expand-btn {
    position: fixed;
    top: 50%;
    left: 0;
    transform: translateY(-50%);
    z-index: 2147483647;
    width: 28px;
    height: 56px;
    background: rgba(18,18,26,0.9);
    border: 1px solid rgba(255,255,255,0.08);
    border-left: none;
    border-radius: 0 8px 8px 0;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    box-shadow: 4px 0 20px rgba(0,0,0,0.5);
    transition: background 0.2s ease-out, border-color 0.2s ease-out, box-shadow 0.2s ease-out;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    font-family: 'Material Symbols Rounded', sans-serif;
    font-size: 18px;
    color: rgba(241,245,249,0.7);
    outline: none;
}
#ag-sidebar-expand-btn:hover {
    background: rgba(99,102,241,0.15);
    border-color: #6366f1;
    color: #6366f1;
    box-shadow: 4px 0 24px rgba(99,102,241,0.35);
}
#ag-sidebar-expand-btn .ag-icon {
    pointer-events: none;
    display: flex;
    align-items: center;
    justify-content: center;
}


/* ── Headings ────────────────────────────────────────────────────── */
h1, h2, h3, h4, h5, h6,
[data-testid="stHeading"] {
    font-family: var(--font) !important;
    color: var(--text) !important;
    letter-spacing: -0.02em;
}
h1 { font-weight: 800 !important; }

/* ── Text & labels ───────────────────────────────────────────────── */
p, label, li, td, th,
.stMarkdown, [data-testid="stMarkdownContainer"],
[data-testid="stText"] {
    font-family: var(--font) !important;
    color: var(--text) !important;
}
.stCaption, [data-testid="stCaptionContainer"] {
    color: var(--text-sec) !important;
}

/* ── Inputs (text_input, text_area, number_input) ────────────────── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stNumberInput"] input {
    background: var(--surface) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text) !important;
    font-family: var(--font) !important;
    transition: var(--transition) !important;
    caret-color: var(--primary) !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus,
[data-testid="stNumberInput"] input:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px var(--primary-glow) !important;
}
[data-testid="stTextInput"] input::placeholder,
[data-testid="stTextArea"] textarea::placeholder {
    color: var(--text-muted) !important;
}

/* ── Selectbox ───────────────────────────────────────────────────── */
[data-testid="stSelectbox"] > div > div {
    background: var(--surface) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text) !important;
    font-family: var(--font) !important;
    cursor: pointer !important;
}
[data-testid="stSelectbox"] input {
    pointer-events: none !important;
    caret-color: transparent !important;
}
[data-testid="stSelectbox"] svg {
    fill: var(--text-sec) !important;
}

/* Selectbox dropdown */
[data-baseweb="popover"] {
    background: var(--surface) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: var(--radius-sm) !important;
}
[data-baseweb="popover"] li {
    color: var(--text) !important;
    font-family: var(--font) !important;
}
[data-baseweb="popover"] li:hover {
    background: var(--glass-hover) !important;
}
[role="option"][aria-selected="true"] {
    background: rgba(99,102,241,0.15) !important;
}

/* ── Buttons ─────────────────────────────────────────────────────── */
.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button {
    background: var(--surface) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text) !important;
    font-family: var(--font) !important;
    font-weight: 600 !important;
    transition: var(--transition) !important;
    cursor: pointer !important;
}
.stButton > button:hover,
.stDownloadButton > button:hover {
    border-color: var(--primary) !important;
    background: rgba(99,102,241,0.08) !important;
    color: var(--text) !important;
}
.stButton > button:active,
.stDownloadButton > button:active {
    transform: scale(0.98) !important;
}

/* Primary CTA button — the form submit */
.stFormSubmitButton > button {
    background: linear-gradient(135deg, var(--primary), var(--secondary)) !important;
    border: none !important;
    color: #fff !important;
    font-weight: 700 !important;
    letter-spacing: 0.02em;
    box-shadow: 0 4px 20px var(--primary-glow) !important;
}
.stFormSubmitButton > button:hover {
    box-shadow: 0 6px 30px rgba(99,102,241,0.5) !important;
    transform: translateY(-1px) !important;
    background: linear-gradient(135deg, var(--primary), var(--secondary)) !important;
}

/* ── Containers / Cards ──────────────────────────────────────────── */
[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"] > div[style*="border"] {
    background: var(--glass) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: var(--radius) !important;
    transition: var(--transition) !important;
}

/* ── Expander ────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    background: var(--glass) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: var(--radius) !important;
    backdrop-filter: blur(12px) !important;
}
[data-testid="stExpander"] summary {
    color: var(--text) !important;
    font-family: var(--font) !important;
    font-weight: 600 !important;
}
[data-testid="stExpander"] summary:hover {
    color: var(--primary) !important;
}

/* ── Metrics ─────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: var(--glass) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: var(--radius) !important;
    backdrop-filter: blur(12px) !important;
    padding: 20px !important;
}
[data-testid="stMetricLabel"] {
    color: var(--text-sec) !important;
    font-family: var(--font) !important;
    font-weight: 500 !important;
}
[data-testid="stMetricValue"] {
    color: var(--text) !important;
    font-family: var(--font) !important;
    font-weight: 700 !important;
}
[data-testid="stMetricDelta"] svg {
    fill: var(--success) !important;
}

/* ── Progress bar ────────────────────────────────────────────────── */
[data-testid="stProgress"] > div > div {
    background: var(--surface) !important;
    border-radius: 99px !important;
}
[data-testid="stProgress"] > div > div > div {
    background: linear-gradient(90deg, var(--primary), var(--secondary)) !important;
    border-radius: 99px !important;
}

/* ── Divider ─────────────────────────────────────────────────────── */
[data-testid="stDivider"],
hr {
    border-color: var(--glass-border) !important;
    opacity: 0.5;
}

/* ── Alerts: info, success, warning, error ────────────────────────── */
[data-testid="stAlert"] {
    border-radius: var(--radius-sm) !important;
    font-family: var(--font) !important;
    backdrop-filter: blur(8px) !important;
}
div[data-testid="stAlert"][data-baseweb="notification"]:has(div[role="alert"]) {
    background: rgba(99,102,241,0.08) !important;
    border-left: 4px solid var(--primary) !important;
}

/* ── Popover ─────────────────────────────────────────────────────── */
[data-testid="stPopover"] > div {
    background: var(--surface) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: var(--radius) !important;
}

/* Popover trigger buttons — action row style */
[data-testid="stPopover"] > button {
    background: var(--glass) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text) !important;
    font-family: var(--font) !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    padding: 10px 16px !important;
    min-height: 42px !important;
    transition: var(--transition) !important;
    cursor: pointer !important;
    backdrop-filter: blur(8px) !important;
}
[data-testid="stPopover"] > button:hover {
    border-color: var(--primary) !important;
    background: rgba(99,102,241,0.08) !important;
    color: var(--text) !important;
}
/* Hide the default chevron arrow on popover buttons */
[data-testid="stPopover"] > button svg {
    display: none !important;
}

/* Popover panel (the floating dropdown content) */
[data-testid="stPopoverBody"],
[data-testid="stPopoverBody"] > div {
    background: var(--surface) !important;
}
/* Ensure inputs & buttons inside popovers share the same surface color */
[data-testid="stPopoverBody"] [data-testid="stSelectbox"] > div > div,
[data-testid="stPopoverBody"] .stDownloadButton > button,
[data-testid="stPopoverBody"] .stButton > button {
    background: var(--surface) !important;
    border: 1px solid var(--glass-border) !important;
}

/* ── Tabs ─────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--text-sec) !important;
    font-family: var(--font) !important;
    font-weight: 500 !important;
    border-radius: var(--radius-xs) !important;
    transition: var(--transition) !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: var(--text) !important;
    background: var(--glass-hover) !important;
}
.stTabs [aria-selected="true"] {
    color: var(--primary) !important;
    background: rgba(99,102,241,0.1) !important;
}
.stTabs [data-baseweb="tab-highlight"] {
    background-color: var(--primary) !important;
}

/* ── Checkbox ────────────────────────────────────────────────────── */
[data-testid="stCheckbox"] label span {
    color: var(--text) !important;
    font-family: var(--font) !important;
}

/* ── Spinner ─────────────────────────────────────────────────────── */
[data-testid="stSpinner"] {
    color: var(--primary) !important;
}
[data-testid="stSpinner"] svg circle {
    stroke: var(--primary) !important;
}

/* ── Chart overrides ─────────────────────────────────────────────── */
[data-testid="stArrowVegaLiteChart"] {
    background: var(--glass) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: var(--radius) !important;
    padding: 12px !important;
    backdrop-filter: blur(12px) !important;
}

/* ── Form ────────────────────────────────────────────────────────── */
[data-testid="stForm"] {
    background: var(--glass) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: var(--radius) !important;
    backdrop-filter: blur(16px) !important;
    padding: 24px !important;
}

/* ── Scrollbar ───────────────────────────────────────────────────── */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: transparent;
}
::-webkit-scrollbar-thumb {
    background: var(--glass-border);
    border-radius: 99px;
}
::-webkit-scrollbar-thumb:hover {
    background: var(--text-muted);
}

/* ── Reduced motion ──────────────────────────────────────────────── */
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        transition-duration: 0.01ms !important;
    }
}

/* ── Custom component classes (used by helpers below) ────────────── */

.glass-card {
    background: var(--glass);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--glass-border);
    border-radius: var(--radius);
    padding: 24px;
    transition: var(--transition);
}
.glass-card:hover {
    border-color: rgba(255,255,255,0.14);
}

.gradient-text {
    background: linear-gradient(135deg, var(--primary), var(--secondary));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.section-header {
    margin-bottom: 8px;
}
.section-header h2 {
    font-family: var(--font);
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--text);
    margin: 0;
}
.section-header p {
    font-family: var(--font);
    font-size: 0.875rem;
    color: var(--text-sec);
    margin: 4px 0 0 0;
}

.stat-card {
    background: var(--glass);
    backdrop-filter: blur(16px);
    border: 1px solid var(--glass-border);
    border-radius: var(--radius);
    padding: 20px 24px;
    display: flex;
    align-items: center;
    gap: 16px;
    transition: var(--transition);
}
.stat-card:hover {
    border-color: rgba(255,255,255,0.14);
}
.stat-card .stat-icon {
    width: 48px;
    height: 48px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.25rem;
    flex-shrink: 0;
}
.stat-card .stat-info {
    flex: 1;
    min-width: 0;
}
.stat-card .stat-label {
    font-family: var(--font);
    font-size: 0.8rem;
    font-weight: 500;
    color: var(--text-sec);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.stat-card .stat-value {
    font-family: var(--font);
    font-size: 1.75rem;
    font-weight: 800;
    color: var(--text);
    line-height: 1.2;
}
.stat-card .stat-delta {
    font-size: 0.8rem;
    font-weight: 600;
    margin-top: 2px;
}
.stat-delta.positive { color: var(--success); }
.stat-delta.negative { color: var(--danger); }

.tag-badge {
    display: inline-flex;
    align-items: center;
    padding: 3px 10px;
    border-radius: 99px;
    font-family: var(--font);
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    line-height: 1.4;
}

.s    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: 10px;
    font-family: var(--font);
    font-weight: 800;
    font-size: 0.9rem;
}

/* ── Shimmer & Skeleton Animations ─────────────────────────────── */
@keyframes skeleton-shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}
.skeleton-card {
    background: linear-gradient(90deg, rgba(255,255,255,0.02) 25%, rgba(255,255,255,0.06) 50%, rgba(255,255,255,0.02) 75%) !important;
    background-size: 200% 100% !important;
    animation: skeleton-shimmer 1.8s infinite linear !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: var(--radius) !important;
    padding: 24px;
    height: 240px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-sizing: border-box;
}
.skeleton-line {
    height: 12px;
    background: rgba(255, 255, 255, 0.04);
    border-radius: 4px;
    margin-bottom: 8px;
}
.skeleton-line.title {
    width: 60%;
    height: 18px;
    margin-bottom: 12px;
}
.skeleton-line.badge {
    height: 18px;
    border-radius: 99px;
    display: inline-block;
    margin-right: 6px;
}
.skeleton-line.preview-1 { width: 90%; }
.skeleton-line.preview-2 { width: 85%; }
.skeleton-line.preview-3 { width: 50%; }
.skeleton-line.footer {
    width: 100%;
    height: 28px;
    margin-top: 12px;
    margin-bottom: 0;
}

/* ── Optimistic UI Animations ─────────────────────────────────── */
@keyframes fade-out-slide {
    0% { opacity: 1; transform: scale(1); max-height: 500px; margin-bottom: inherit; padding: inherit; }
    100% { opacity: 0; transform: scale(0.9) translateY(10px); max-height: 0; margin-bottom: 0; padding: 0; border: none; overflow: hidden; display: none; }
}
.fade-out {
    animation: fade-out-slide 0.35s cubic-bezier(0.4, 0, 0.2, 1) forwards !important;
}

@keyframes pulsing-border {
    0% { border-color: var(--glass-border); box-shadow: 0 0 0 rgba(99,102,241,0); }
    50% { border-color: var(--primary); box-shadow: 0 0 15px rgba(99,102,241,0.2); }
    100% { border-color: var(--glass-border); box-shadow: 0 0 0 rgba(99,102,241,0); }
}
.pulsing-glow {
    animation: pulsing-border 2s infinite ease-in-out !important;
}

/* ── Library card redesign ───────────────────────────────────────── */

/* Card footer separator */
.card-footer {
    margin-top: 16px;
    padding-top: 14px;
    border-top: 1px solid var(--glass-border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
}

/* Selection toggle pill */
.sel-toggle {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 10px;
    border-radius: 99px;
    border: 1px solid var(--glass-border);
    background: transparent;
    color: var(--text-sec);
    font-family: var(--font);
    font-size: 0.72rem;
    font-weight: 500;
    cursor: pointer;
    transition: var(--transition);
    user-select: none;
    white-space: nowrap;
}
.sel-toggle:hover {
    border-color: var(--primary);
    color: var(--primary);
    background: rgba(99,102,241,0.08);
}
.sel-toggle.active {
    border-color: var(--primary);
    color: var(--primary);
    background: rgba(99,102,241,0.12);
}
.sel-toggle .sel-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--glass-border);
    transition: var(--transition);
    flex-shrink: 0;
}
.sel-toggle.active .sel-dot {
    background: var(--primary);
    box-shadow: 0 0 6px rgba(99,102,241,0.6);
}

/* Icon action button row */
.card-actions {
    display: flex;
    align-items: center;
    gap: 4px;
}
.card-action-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 5px;
    min-width: 44px;
    min-height: 34px;
    padding: 6px 10px;
    border-radius: var(--radius-xs);
    border: 1px solid transparent;
    background: transparent;
    color: var(--text-sec);
    font-family: var(--font);
    font-size: 0.72rem;
    font-weight: 500;
    cursor: pointer;
    transition: var(--transition);
    text-decoration: none;
}
.card-action-btn svg {
    width: 14px;
    height: 14px;
    stroke: currentColor;
    fill: none;
    stroke-width: 2;
    stroke-linecap: round;
    stroke-linejoin: round;
    flex-shrink: 0;
}
.card-action-btn:hover {
    background: var(--glass-hover);
    border-color: var(--glass-border);
    color: var(--text);
}
.card-action-btn.danger:hover {
    background: rgba(239,68,68,0.1);
    border-color: rgba(239,68,68,0.3);
    color: var(--danger);
}
.card-action-btn:disabled,
.card-action-btn[disabled] {
    opacity: 0.35;
    cursor: not-allowed;
    pointer-events: none;
}

/* Card Action Buttons Overrides (within card containers) */
[data-testid="stVerticalBlockBorderWrapper"] .stButton > button,
[data-testid="stVerticalBlockBorderWrapper"] .stDownloadButton > button,
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stPopover"] > button {
    background: rgba(255, 255, 255, 0.02) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: var(--radius-xs) !important;
    color: var(--text-sec) !important;
    font-family: var(--font) !important;
    font-size: 0.8rem !important;
    font-weight: 600 !important;
    padding: 6px 12px !important;
    min-height: 34px !important;
    transition: var(--transition) !important;
    cursor: pointer !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 6px !important;
    width: 100% !important;
}

/* Hover effects for duplicate, download, and delete popovers using id selectors */
[data-testid="stVerticalBlockBorderWrapper"] button[id*="dup_"]:hover {
    border-color: var(--primary) !important;
    background: rgba(99, 102, 241, 0.08) !important;
    color: var(--text) !important;
}

[data-testid="stVerticalBlockBorderWrapper"] button[id*="dl_"]:hover {
    border-color: var(--secondary) !important;
    background: rgba(6, 182, 212, 0.08) !important;
    color: var(--text) !important;
}

/* Delete popover button default state - solid red background */
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stPopover"] button {
    background: var(--danger) !important;
    border-color: var(--danger) !important;
    color: #ffffff !important;
}

/* Delete popover button hover state */
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stPopover"] button:hover {
    background: #dc2626 !important;
    border-color: #dc2626 !important;
    color: #ffffff !important;
    box-shadow: 0 0 12px rgba(239, 68, 68, 0.4) !important;
}

/* Hide chevron/arrow in popover button */
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stPopover"] button svg {
    display: none !important;
}

/* Checkbox re-style inside cards */
.lib-card-sel [data-testid="stCheckbox"] {
    font-size: 0.82rem !important;
    color: var(--text) !important;
}
.lib-card-sel [data-testid="stCheckbox"] label {
    font-size: 0.82rem !important;
    color: var(--text) !important;
    font-weight: 500 !important;
    gap: 8px !important;
}

/* Pagination bar */
.lib-pagination {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    margin-top: 8px;
}
.lib-pagination .stButton > button {
    min-width: 100px !important;
    border-radius: 99px !important;
}

</style>
"""


# ---------------------------------------------------------------------------
# Sidebar portal JS — fixes the expand button disappearing when collapsed
# ---------------------------------------------------------------------------

# Streamlit's stAppViewContainer has overflow:hidden + CSS transforms which
# clip position:fixed children.  We work around this by portalling a real
# <button> directly onto document.body that proxies clicks to the real button.

_SIDEBAR_JS = """
<script>
(function () {
  'use strict';

  // We run inside a components.v1.html iframe, so use window.parent to
  // reach the actual Streamlit page document.
  var doc = window.parent.document;
  var BTN_ID = 'ag-sidebar-expand-btn';

  function createPortalBtn() {
    if (doc.getElementById(BTN_ID)) return;
    var btn = doc.createElement('button');
    btn.id = BTN_ID;
    btn.setAttribute('aria-label', 'Expand sidebar');
    btn.title = 'Expand sidebar';
    btn.innerHTML = '<span class="ag-icon"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg></span>';
    btn.addEventListener('click', function () {
      var real = doc.querySelector('[data-testid="stExpandSidebarButton"]');
      if (real) real.click();
    });
    doc.body.appendChild(btn);
  }

  function removePortalBtn() {
    var btn = doc.getElementById(BTN_ID);
    if (btn) btn.remove();
  }

  function syncState() {
    var expandBtn = doc.querySelector('[data-testid="stExpandSidebarButton"]');
    if (expandBtn) {
      createPortalBtn();
    } else {
      removePortalBtn();
    }
  }

  syncState();
  var observer = new MutationObserver(syncState);
  observer.observe(doc.body, { childList: true, subtree: true });
  
  // Custom toast observer to match style
  function styleToasts() {
    var toasts = doc.querySelectorAll('[data-testid="stToast"]');
    toasts.forEach(function(toast) {
      toast.style.background = 'rgba(18, 18, 26, 0.95)';
      toast.style.backdropFilter = 'blur(16px)';
      toast.style.border = '1px solid rgba(255, 255, 255, 0.08)';
      toast.style.borderRadius = '12px';
      toast.style.color = '#f1f5f9';
      toast.style.boxShadow = '0 8px 32px rgba(0,0,0,0.4)';
    });
  }
  styleToasts();
  var toastObserver = new MutationObserver(styleToasts);
  toastObserver.observe(doc.body, { childList: true, subtree: true });
})();
</script>
"""

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def inject_theme() -> None:
    """Inject the complete CSS theme into the page.  Call once at the top of
    every page **after** ``st.set_page_config``."""
    import streamlit.components.v1 as _components
    st.markdown(_CSS, unsafe_allow_html=True)
    # Inject JS via an iframe component; the script reaches the parent page
    # through window.parent.document to portal the sidebar expand button.
    _components.html(_SIDEBAR_JS, height=0)


# -- Component helpers (return HTML strings) --------------------------------


def gradient_text(text: str, tag: str = "span") -> str:
    """Wrap *text* in a gradient-filled element."""
    return f'<{tag} class="gradient-text">{text}</{tag}>'


def section_header(title: str, subtitle: str = "") -> str:
    """Styled section heading with optional subtitle."""
    sub = f"<p>{subtitle}</p>" if subtitle else ""
    return f'<div class="section-header"><h2>{title}</h2>{sub}</div>'


def gradient_divider() -> str:
    """A subtle gradient horizontal rule."""
    return '<div class="gradient-divider"></div>'


def glass_card(content: str, extra_style: str = "") -> str:
    """Wrap *content* in a glassmorphism card."""
    style = f' style="{extra_style}"' if extra_style else ""
    return f'<div class="glass-card"{style}>{content}</div>'


def stat_card(label: str, value: str, icon: str = "", bg_color: str = "rgba(99,102,241,0.12)", icon_color: str = "#6366f1", delta: str = "") -> str:
    """KPI stat card with icon, value, label, and optional delta."""
    delta_html = ""
    if delta:
        cls = "positive" if delta.startswith("+") else "negative"
        delta_html = f'<div class="stat-delta {cls}">{delta}</div>'
    icon_html = f'<div class="stat-icon" style="background:{bg_color}; color:{icon_color}">{icon}</div>' if icon else ""
    return (
        f'<div class="stat-card">'
        f'{icon_html}'
        f'<div class="stat-info">'
        f'<div class="stat-label">{label}</div>'
        f'<div class="stat-value">{value}</div>'
        f'{delta_html}'
        f'</div></div>'
    )


def tag_badge(text: str, color: str = "#6366f1") -> str:
    """Coloured pill badge."""
    bg = color.replace(")", ",0.12)").replace("rgb", "rgba") if color.startswith("rgb") else f"{color}1f"
    # For hex colours, append 1f (≈12% opacity) for the background
    if color.startswith("#"):
        bg = color + "1f"
    return f'<span class="tag-badge" style="background:{bg}; color:{color}">{text}</span>'


TYPE_COLORS: dict[str, str] = {
    "tts": "#6366f1",
    "music": "#06b6d4",
    "sfx": "#f59e0b",
    "voiceover": "#22c55e",
}


def type_badge(audio_type: str) -> str:
    """Render a type pill badge with the standard colour for that type."""
    color = TYPE_COLORS.get(audio_type, "#6366f1")
    return tag_badge(audio_type.upper(), color)


def score_ring(score: float, size: int = 80) -> str:
    """SVG circular score indicator.

    *score* is 0–100.  Returns an SVG string.
    """
    score = max(0, min(100, score))
    r = (size - 8) / 2
    cx = cy = size / 2
    circumference = 2 * 3.14159 * r
    offset = circumference * (1 - score / 100)
    # Pick colour based on score
    if score >= 75:
        color = COLORS["success"]
    elif score >= 50:
        color = COLORS["warning"]
    else:
        color = COLORS["danger"]
    font_size = size * 0.28
    return (
        f'<div class="score-ring-container" style="position:relative;width:{size}px;height:{size}px">'
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="var(--glass-border)" stroke-width="4" />'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="4" '
        f'stroke-dasharray="{circumference}" stroke-dashoffset="{offset}" '
        f'stroke-linecap="round" transform="rotate(-90 {cx} {cy})" '
        f'style="transition: stroke-dashoffset 0.6s ease-out" />'
        f'</svg>'
        f'<span class="score-label" style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);font-size:{font_size}px;font-weight:700;color:{color}">{score:.0f}</span>'
        f'</div>'
    )


def hero_section(title_html: str, subtitle: str = "") -> str:
    """Large hero heading for pages."""
    sub = f'<p class="hero-subtitle">{subtitle}</p>' if subtitle else ""
    return f'<div style="margin-bottom:32px"><h1 class="hero-title">{title_html}</h1>{sub}</div>'


def feature_card(icon: str, title: str, description: str, icon_bg: str = "rgba(99,102,241,0.12)", icon_color: str = "#6366f1") -> str:
    """Feature card for the landing page."""
    return (
        f'<div class="feature-card">'
        f'<div class="fc-icon" style="background:{icon_bg};color:{icon_color}">{icon}</div>'
        f'<div class="fc-title">{title}</div>'
        f'<p class="fc-desc">{description}</p>'
        f'</div>'
    )


def prompt_display(text: str) -> str:
    """Monospaced prompt display block."""
    import html as _html
    escaped = _html.escape(text)
    return f'<div class="prompt-display">{escaped}</div>'


def api_status_pill(url: str) -> str:
    """Small pill showing API connectivity."""
    return (
        f'<div class="api-status">'
        f'<span class="dot green"></span>'
        f'<span style="color:var(--text-sec)">API connectée sur {url}</span>'
        f'</div>'
    )


def rank_badge(rank: int) -> str:
    """Numbered rank badge with gold/silver/bronze styling."""
    colors = {
        1: ("rgba(250,204,21,0.12)", "#facc15"),
        2: ("rgba(148,163,184,0.12)", "#94a3b8"),
        3: ("rgba(217,119,6,0.12)", "#d97706"),
    }
    bg, fg = colors.get(rank, ("var(--glass)", "var(--text-sec)"))
    return f'<span class="rank-badge" style="background:{bg};color:{fg}">#{rank}</span>'


def render_sidebar() -> None:
    """Render the sidebar branding and custom navigation links."""
    with st.sidebar:
        st.markdown(
            '<div style="padding:16px 0 8px 0">'
            f'<span style="font-family:var(--font);font-size:1.15rem;font-weight:800;letter-spacing:-0.02em">'
            f'{gradient_text("PromptAudio")}'
            "</span>"
            '<p style="font-size:0.75rem;color:var(--text-muted);margin:4px 0 0 0">Générateur de prompts IA</p>'
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown('<div style="margin-top: 16px"></div>', unsafe_allow_html=True)
        st.page_link("pages/generate.py", label="Générer", icon="✨")
        st.page_link("pages/library.py", label="Bibliothèque", icon="📚")


def loading_skeleton_grid(count: int = 6) -> str:
    """Return raw HTML string representing a grid of shimmering skeleton cards."""
    cards = []
    for _ in range(count):
        card_html = (
            '<div class="skeleton-card">'
            '  <div>'
            '    <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px">'
            '      <div class="skeleton-line title"></div>'
            '      <div class="skeleton-line" style="width:36px; height:36px; border-radius:50%"></div>'
            '    </div>'
            '    <div style="margin-bottom:16px; display:flex; gap:6px">'
            '      <div class="skeleton-line badge" style="width:50px"></div>'
            '      <div class="skeleton-line badge" style="width:70px"></div>'
            '    </div>'
            '    <div class="skeleton-line preview-1"></div>'
            '    <div class="skeleton-line preview-2"></div>'
            '    <div class="skeleton-line preview-3"></div>'
            '  </div>'
            '  <div class="skeleton-line footer"></div>'
            '</div>'
        )
        cards.append(card_html)
    
    grid_html = (
        '<div style="display:grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap:24px; width:100%">'
        + "".join(cards) +
        '</div>'
    )
    return grid_html


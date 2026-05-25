# 🎨 PLAN — UI Redesign: Premium Dark Glassmorphism

> **Task**: Redesign the entire Streamlit frontend with a modern, premium SaaS aesthetic  
> **Approach**: Keep Streamlit + inject heavy custom CSS/HTML via `st.markdown`  
> **Visual Direction**: Dark mode, glassmorphism, subtle gradients, neon accents  
> **Language**: French (unchanged)  
> **Backend**: Untouched — all existing FastAPI endpoints remain as-is

---

## 1. Current State Analysis

### What exists today

| File | Lines | Current State |
|------|-------|---------------|
| `frontend/app.py` | 36 | Bare `st.title` + `st.markdown` welcome. Default Streamlit chrome. |
| `frontend/pages/1_Generate.py` | 255 | `st.form` + `st.text_area` + popovers. Fully functional but stock look. |
| `frontend/pages/2_Library.py` | 250 | 3-col card grid, checkboxes for bulk export, pagination buttons. Stock. |
| `frontend/pages/3_Analytics.py` | 132 | `st.metric`, `st.bar_chart`, `st.line_chart`. Completely vanilla. |

### Problems with the current UI

1. **100% default Streamlit** — white background, system fonts, no custom styling
2. **No visual identity** — generic emoji titles, no logo, no brand color
3. **Poor visual hierarchy** — form inputs, results, and actions are laid out with no breathing room
4. **No micro-interactions** — no hover states, no transitions, no loading animations
5. **Cards are just `st.container(border=True)`** — no depth, no glass effect
6. **Charts are plain `st.bar_chart`** — no custom colors, no styling
7. **Sidebar is completely unstyled** — default Streamlit navigation

---

## 2. Design System

### 2.1 Color Palette

```
Background:        #0a0a0f (near-black)
Surface:           #12121a (card background)
Glass:             rgba(255,255,255,0.04) with backdrop-blur(16px)
Glass border:      rgba(255,255,255,0.08)
Glass hover:       rgba(255,255,255,0.08)

Primary accent:    #6366f1 (indigo-500)
Primary glow:      rgba(99,102,241,0.3)
Secondary accent:  #06b6d4 (cyan-500)
Success:           #22c55e
Warning:           #f59e0b
Danger:            #ef4444

Text primary:      #f1f5f9 (slate-100)
Text secondary:    #94a3b8 (slate-400)
Text muted:        #475569 (slate-600)
```

### 2.2 Typography

- **Headings**: `Inter` (700) — clean geometric sans-serif
- **Body**: `Inter` (400/500)
- **Monospace**: `JetBrains Mono` — for prompt content and code blocks
- Import via Google Fonts CDN in the injected CSS

### 2.3 Spacing & Radius

- Card padding: `24px`
- Card border-radius: `16px`
- Button border-radius: `12px`
- Section gap: `32px`
- Glass blur: `backdrop-filter: blur(16px)`

### 2.4 Elevation & Effects

- **Glass cards**: Semi-transparent bg + border + blur + subtle inner glow
- **Neon glow on primary buttons**: `box-shadow: 0 0 20px rgba(99,102,241,0.4)`
- **Hover states**: Border brightens, slight scale(1.01) on cards
- **Score ring**: Animated SVG circular progress (replaces `st.progress`)
- **Loading**: Pulsing gradient shimmer skeleton (replaces `st.spinner`)

---

## 3. Proposed Changes

### Architecture: New shared style module

We will create a `frontend/theme.py` module that injects the complete CSS theme + reusable HTML component helpers. Every page imports from this single source.

```
frontend/
├── theme.py              ← [NEW] CSS injection + HTML component helpers
├── app.py                ← [MODIFY] Landing page redesign
└── pages/
    ├── 1_Generate.py     ← [MODIFY] Full visual overhaul
    ├── 2_Library.py      ← [MODIFY] Full visual overhaul
    └── 3_Analytics.py    ← [MODIFY] Full visual overhaul
```

---

### 3.1 [NEW] `frontend/theme.py` — Design System Core

**Purpose**: Single file that injects the entire CSS theme and exposes HTML helper functions.

**Contents**:

1. **`inject_theme()`** — Called once per page. Injects via `st.markdown(unsafe_allow_html=True)`:
   - Google Fonts import (`Inter`, `JetBrains Mono`)
   - CSS reset for Streamlit defaults (hide hamburger menu, footer, header decoration)
   - Custom CSS for `.stApp` background (dark gradient)
   - Custom sidebar styling (glass effect, custom nav items)
   - Override Streamlit widget styles: buttons, inputs, selectboxes, text areas, metrics, expanders
   - Animated gradient borders, hover transitions
   - Responsive breakpoints

2. **HTML component helpers** (return raw HTML strings for `st.markdown`):
   - `glass_card(content, accent_color)` — renders a glassmorphism container
   - `score_ring(score, size)` — SVG circular progress with animated fill
   - `stat_card(label, value, icon, delta)` — KPI stat with icon + optional delta
   - `tag_badge(text, color)` — colored pill badge for tags and types
   - `section_header(title, subtitle)` — styled section heading with gradient underline
   - `gradient_divider()` — a gradient horizontal rule (replaces `st.divider`)
   - `loading_skeleton()` — shimmer placeholder

---

### 3.2 [MODIFY] `frontend/app.py` — Landing / Home Page

**Current**: Plain `st.title` + `st.markdown` with bullet list + `st.info` API status.

**Redesign**:

- **Hero section**: Large gradient headline "Générateur de Prompts Audio" with animated gradient text
- **Three feature cards** (glass): Générer / Bibliothèque / Analytics — each with icon, short description, and link
- **API status pill**: Minimal green/red dot indicator (replaces `st.info` block)
- **Background**: Subtle radial gradient blobs in the background (CSS only, no JS)
- Remove default Streamlit sidebar title; replace with custom styled logo area

**Logic changes**: None. Same API_BASE session state.

---

### 3.3 [MODIFY] `frontend/pages/1_Generate.py` — Generation Page

**Current**: `st.form` → plain text areas → `st.progress` bar → popovers for save/optimize/export.

**Redesign**:

1. **Input section** (glass card):
   - Styled `st.text_area` with custom dark background, subtle border glow on focus
   - Three selectors in a row with custom-styled `st.selectbox` (overridden via CSS)
   - Primary CTA button: Gradient background (`indigo→cyan`), neon glow on hover
   
2. **Result section** (glass card, only visible after generation):
   - **Score ring** (SVG): Large animated circular score indicator (replaces progress bar)
   - Prompt content in a styled monospace block with copy button
   - Score dimension breakdown: 5 mini radial charts or colored bar segments
   
3. **Action buttons row** (3 glass-styled buttons):
   - 💾 Sauvegarder / 🔄 Optimiser / 📤 Exporter
   - Each uses popovers (unchanged logic) but with restyled popover backgrounds
   
4. **Variants section**: Styled expandable cards instead of bare expanders
5. **Explanation section**: Styled expandable card

**Logic changes**: None. All API calls, session state, and rerun logic remain identical.

---

### 3.4 [MODIFY] `frontend/pages/2_Library.py` — Library Page

**Current**: Text input + selectbox filters → 3-col grid of `st.container(border=True)` → bottom pagination.

**Redesign**:

1. **Search bar** (full-width glass input):
   - Styled with search icon (CSS pseudo-element), rounded edges
   - Filters (type, min score) as compact pill selectors beneath

2. **Results summary**: Muted text with count + active filter badges

3. **Card grid** (3 columns):
   - Each card is a **glass card** with:
     - Type badge (colored pill: TTS=indigo, Music=cyan, SFX=amber, Voiceover=green)
     - Title in semi-bold
     - Score ring (small, inline)
     - Tag pills
     - Prompt preview (2–3 lines, muted text)
     - Action icons row: duplicate / export / delete with hover glow
   - Checkbox for bulk select: styled toggle instead of default checkbox
   - Hover: card border brightens, slight lift

4. **Bulk export bar** (sticky bottom glass bar when items are selected):
   - Count badge, format selector, download button

5. **Pagination**: Styled prev/next buttons with page indicator

**Logic changes**: None. Same `fetch_prompts`, same session state, same API calls.

---

### 3.5 [MODIFY] `frontend/pages/3_Analytics.py` — Dashboard Page

**Current**: 4 `st.metric` widgets → 2 `st.bar_chart` → 1 `st.line_chart` → top 5 list.

**Redesign**:

1. **KPI row** (4 glass stat cards):
   - Each with icon, value, label, and optional delta
   - Subtle gradient accent on the left border of each card

2. **Charts section** (2-col layout):
   - **Score by type**: Styled `st.bar_chart` with custom CSS colors (or Plotly if adding dependencies is acceptable — fallback to styled `st.bar_chart` via CSS override)
   - **Score distribution**: Same approach
   - Charts inside glass cards with proper headings

3. **Timeline chart** (full-width glass card):
   - `st.line_chart` with CSS-overridden colors

4. **Top 5 leaderboard** (glass cards):
   - Rank number with gradient text (#1 = gold, #2 = silver, etc.)
   - Glass card per entry with score ring + type badge + preview

**Logic changes**: None. Same data fetching and processing.

---

## 4. Implementation Order

| Phase | Files | Description | Estimated Effort |
|-------|-------|-------------|-----------------|
| **Phase 1** | `theme.py` | Build the entire design system: CSS injection + HTML helpers | Core foundation |
| **Phase 2** | `app.py` | Redesign landing page | Light — smallest page |
| **Phase 3** | `1_Generate.py` | Redesign generation page | Medium — most interactive |
| **Phase 4** | `2_Library.py` | Redesign library page | Medium — complex grid |
| **Phase 5** | `3_Analytics.py` | Redesign analytics dashboard | Medium — charts + KPIs |
| **Phase 6** | Visual QA | Run the app, screenshot, verify all pages | Verification pass |

---

## 5. Constraints & Rules

1. **No backend changes** — All modifications are strictly in `frontend/`
2. **No new Python dependencies** — Everything is CSS/HTML injection via `st.markdown(unsafe_allow_html=True)`. No Plotly, no Dash, no additional packages.
3. **All existing functionality preserved** — Every API call, every session_state key, every form submission must work exactly as before
4. **Responsive** — CSS should handle standard desktop widths (Streamlit's own responsive behavior for mobile is limited, but we won't break it)
5. **No JavaScript dependencies** — Pure CSS animations and transitions only (Streamlit sandbox limits JS execution)
6. **French language** — All labels, titles, placeholders remain in French

---

## 6. Verification Plan

### Visual Verification
- Run `streamlit run frontend/app.py` and visually inspect all 4 pages
- Verify dark theme applies globally (no white flashes, no unstyled Streamlit elements)
- Check glassmorphism effect on cards
- Verify hover states on buttons and cards
- Confirm score ring renders correctly at various scores (0, 50, 75, 100)

### Functional Verification
- Generate a prompt → verify result displays in new styled layout
- Optimize a prompt → verify score before/after renders correctly
- Save to library → verify it appears in the library page
- Search and filter in library → verify results update
- Export JSON and Markdown → verify download triggers
- Duplicate and delete prompts → verify rerun works
- Check analytics with data → verify all charts render
- Check analytics with no data → verify empty state message

### Regression Checks
- All `st.session_state` keys still work
- API connection error states still display
- Pagination still functions
- Bulk export still works
- All popovers still open and submit correctly

---

## 7. Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Streamlit CSS overrides may break on version update | Pin `streamlit>=1.35.0` (already done). Use specific selectors, not wildcards. |
| `unsafe_allow_html` has limited support for some HTML | Stick to `div`, `span`, `svg`, `style` — all well-supported. No `script` tags. |
| Some Streamlit widgets have deeply nested DOM structures | Inspect with browser devtools to find correct CSS selectors. Use `!important` sparingly. |
| SVG score ring may not render in `st.markdown` | Fallback: use a pure CSS circular progress with `conic-gradient`. |

---

*Plan created for: UI Redesign — Premium Dark Glassmorphism*

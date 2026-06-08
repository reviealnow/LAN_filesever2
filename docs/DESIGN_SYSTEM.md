# Dashboard Design System

A portable design system distilled from the Luna **"Spacing – Dashboards"** reference
and implemented in this app. Use it to keep this project consistent **and** to transfer
the look-and-feel to other projects.

> The canonical implementation lives in this repo: `templates/base.html`,
> `templates/files.html`, `static/styles.css`, `app.py`, `file_service.py`.
> Design source: `reference/Spacing – Dashboards.png` (the `spacing-dashboard.html`
> alongside it is only the zeroheight app shell — **the PNG is the real reference**).

---

## 1. What the reference teaches

1. **App shell** — left sidebar (nav) + sticky top toolbar (title, search, primary
   action) wrapping a scrollable content area.
2. **One spacing scale, everywhere** — the literal point of the reference. No ad-hoc margins.
3. **Uniform card chrome** — every widget = `title + subtitle + optional action slot`,
   identical gutters.
4. **Restrained palette** — neutral greys + a *single* accent colour.
5. **Density with breathing room** — KPI row up top, card grid below.

---

## 2. Design tokens

Copy the `:root` block verbatim; rebrand by changing only `--accent` / `--accent-weak`.

```css
:root{
  --space-1:4px; --space-2:8px; --space-3:12px; --space-4:16px;
  --space-5:24px; --space-6:32px; --space-7:48px; --space-8:64px;
  --bg:#f4f6fa; --panel:#fff; --ink:#1b2333; --muted:#687389; --faint:#9aa4b8;
  --accent:#1565c0; --accent-weak:#e8f0fb;            /* ← rebrand here */
  --ok:#0c7a43; --ok-weak:#e4f4ea; --danger:#b3261e; --danger-weak:#fce8e6;
  --border:#e3e8f0; --shadow:0 1px 2px rgba(20,30,55,.04),0 6px 20px rgba(20,30,55,.06);
  --radius:14px; --sidebar-w:232px;
}
```

**Rule:** every padding/gap/margin references a `--space-*` token; all accent colour comes
from `--accent` / `--accent-weak`.

---

## 3. Component inventory

| Component | Key classes | Notes |
|---|---|---|
| **App shell** | `.app` (grid `var(--sidebar-w) 1fr`), `.sidebar`, `.toolbar`, `.content` | Shell only when authenticated; signed-out pages use `.auth-shell`. Define one `{% block content %}` and call `{{ self.content() }}` in the other layout branch to avoid Jinja "block defined twice". |
| **KPI card** | `.kpis` (grid `repeat(4,1fr)`), `.kpi`, `.kpi-label/-value/-sub` | Feed from data the app **already has** — don't invent metrics. |
| **Card chrome** | `.card`, `.card-head`, `.card-titles`, `.card-sub`, `.card-body` | The reusable unit — every widget is one. |
| **Table + icon actions** | `.row-actions`, `.icon-btn`, `.icon-btn.danger` | 30px soft-tint icon buttons; manage borders in *all* states so a global `button:hover` can't leak a grey edge. Destructive form gets `onsubmit="return confirm(...)"`. |
| **Activity feed** | `.feed`, `.feed-item`, `.feed-dot` | Merge multiple sources by timestamp, server-side. |
| **Charts (SVG)** | `.chart-svg`, `.donut`, `.donut-legend`, `.barrow*` | See §4. |
| **Auth shell / forms** | `.auth-shell`, `.form-panel` | Logged-out hero / login / register. |
| **Toasts / flash** | `.toast-container`, `.toast`, `.flash` | Auto-dismiss JS in `base.html`. |
| **Responsive** | breakpoints **1100px** (grid → 1 col, KPIs → 2 col) and **720px** (sidebar → top bar, KPIs → 1 col) | |

---

## 4. Charts

**Decision: server-rendered inline SVG, not Chart.js.**

Rationale (carry this over): this is an **offline-first LAN** context, so a CDN may not
load. Inline SVG is zero-dependency, server-rendered, and themable with the same tokens.
Use Chart.js only if you need hover tooltips / axis auto-scaling — and then **vendor it
into `static/`**, never a CDN.

**B-ready pattern (do this regardless of renderer):** compute aggregates → build a
JSON-serializable `charts` dict in the route → render SVG from it in Jinja **and** emit:

```html
<script id="chart-data" type="application/json">{{ charts | tojson }}</script>
```

Swapping to Chart.js later then needs **zero backend change**.

Three recipes (full source in `templates/files.html` + `file_service.py`):

- **Bar (time series):** `uploads_per_day(14)` zero-filled → Jinja loop computing
  `x` / `height` from the max value, with 3 Y-gridlines + day labels.
- **Donut:** percentages → stacked `<circle r="15.915">` with
  `stroke-dasharray="{{pct}} {{100-pct}}"` and a running `stroke-dashoffset`
  (Jinja `namespace` to accumulate the offset).
- **Horizontal bars:** width `= val / max * 100%`, shade ramp per rank.

A side-by-side SVG-vs-Chart.js MVP (same data) is preserved in
`mockups/charts-svg.html` and `mockups/charts-chartjs.html`.

---

## 5. Non-negotiables

- **`SECRET_KEY` from env** with a random `secrets.token_hex` fallback — never a hardcoded
  default. (Set the env var in production so sessions survive restarts.)
- **Verify on real data, not just mockups.** `mockups/run_preview.py` seeds a *throwaway
  temp DB* and serves the real app over HTTP, so screenshots use real rendering while the
  real instance DB is untouched. Seed must be realistic (e.g. back-dated rows) or
  time-series charts look flat.
- The preview server has **no reloader** → restart after template edits.
- **Commit hygiene:** split **feature** commits from **chore/mockup** commits.

---

## 6. Applying this to a new project

1. Copy `reference/Spacing – Dashboards.png` and this doc into the new project.
2. Copy the `:root` token block; rebrand `--accent` / `--accent-weak`.
3. Build the shell (`base.html` pattern), then the KPI row from the new app's real data,
   then one `.card` per widget.
4. Charts as inline SVG; emit the JSON blob for a future Chart.js swap.
5. Work on a branch; show mockups/screenshots before wiring; verify on seeded real data;
   keep secrets out of source; don't commit until approved.

Kickoff prompt for a fresh session:

```
I'm applying an existing dashboard design system to <NEW_PROJECT> at <PATH>.

Design source: reference/Spacing – Dashboards.png (Luna). Canonical
implementation to mirror: the LAN_filesever2 repo (templates/base.html,
templates/files.html, static/styles.css, app.py, file_service.py) and its
docs/DESIGN_SYSTEM.md — copy its patterns, not its domain content.

Apply: app shell (sidebar + sticky toolbar + content, shell only when
authenticated); one spacing-token scale + a SINGLE accent (rebrand via
--accent/--accent-weak); KPI row from data the app ALREADY has; uniform card
chrome for every widget; tables with 30px soft-tint icon buttons + confirm()
on destructive actions; charts as server-rendered inline SVG that also emit
the data as <script type="application/json"> (Chart.js only if interactivity
is needed, vendored locally — never CDN).

Process: branch; show mockups/screenshots before wiring; verify on seeded
real data (throwaway DB), not just mockups; keep SECRET_KEY/secrets out of
source; don't commit until I approve; split feature vs mockup commits.

Start by reading the reference PNG + the canonical files, then propose how the
shell + KPIs + cards map onto <NEW_PROJECT>'s actual data.
```

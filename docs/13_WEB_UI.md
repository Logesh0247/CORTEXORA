# CORTEXORA Web — the custom interactive UI

Streamlit's widget chrome has a visual ceiling, so CORTEXORA also ships a bespoke web front-end:

- **`web/static/index.html`** — a single-page app with its own design system (dark glass, gradient accents). No framework, no build step, no CDN dependency.
- **`web/server.py`** — a stdlib-only Python server (no new dependencies) that serves the page and a JSON API backed by the *same* analytics as the Streamlit app: `GET /api/dashboard` (KPIs + deltas, trend with breakdowns, categories, regions, product leaderboard, insights — all filterable by period/metric/granularity/category/region/channel) and `POST /api/chat` (the Phase-11 data-grounded assistant).

Run it:
```bash
.venv/bin/python web/server.py        # http://localhost:8502
```
The Streamlit app (port 8501) remains fully functional; the web UI is an additional, faster, fully client-interactive surface over identical calculations. Client-side interactions (presets, chips, clickable category bars, product selection, scenario sliders) feel instant; anything needing real analytics calls the API.

# Next.js UI — Architecture (per Master Prompt §13)

## Existing stack found (kept, not replaced)
- Python analytics/ML core in `cortexora/` (metrics, forecasting, churn, optimization, experiments, decision engine, monitoring, assistant) — **unchanged**.
- SQLite warehouse + ETL (`scripts/run_etl.py`), Streamlit app (`app.py`, full legacy UI), stdlib web API (`web/server.py`).
- Decision per prompt §2: new frontend in **Next.js/React/TypeScript + Tailwind + Recharts + Lucide + Framer Motion**, connected through a new **FastAPI adapter** (`api/main.py`) that imports and exposes the existing Python functions. No analytics are reimplemented in TypeScript (prompt §9: no competing metric definitions). No secrets in frontend; Copilot calls go browser → FastAPI → deterministic demo assistant (labelled demo mode; an LLM provider can be configured server-side later via env, never in client code).

## Navigation architecture (routes = prompt §4A)
OVERVIEW: `/` Home · `/executive` Executive Intelligence
ANALYTICS: `/growth` · `/marketing` · `/customers` · `/pricing`
PREDICTION & PLANNING: `/forecasting` · `/mmm` · `/experiments`
INTELLIGENCE: `/decisions` · `/market-radar` · `/health`
WORKSPACE: `/reports` · `/data-sources` · `/settings`
Plus persistent **Copilot drawer** (floating button, page-context prompts), **command palette (Ctrl/⌘K)**, collapsible sidebar, mobile drawer, dark/light theme persisted in localStorage, global date/dataset context reflected in URL query params.

## Design system
Tokens (CSS variables, both themes): bg `#070d18`/#f4f7fb, panel, border, text/muted, accents indigo `#6366f1`, electric blue `#38bdf8`, violet `#a78bfa`, success/warn/danger. Inter font, 12–16px radii, soft borders, restrained shadows. Reusable components: `Shell` (sidebar+topbar), `KpiCard`, `ChartCard`, `DataTable` (sort/search/paginate), `Section`, `StateBlock` (loading/empty/error), `Copilot`, `CommandPalette`. Reduced-motion respected via media query; focus-visible rings; semantic landmarks.

## Backend connection (FastAPI, `api/main.py`, port 8000)
Reuses `web.server.dashboard/chat` computations and `cortexora.*` directly:
`GET /api/health · /api/dashboard · /api/growth · /api/forecast · /api/customers · /api/marketing · /api/pricing · /api/mmm · /api/experiments · /api/decisions (+POST status/outcome) · /api/health-data · /api/datasources · POST /api/upload/analyse · /api/reports/executive · POST /api/chat`
CORS is restricted to the local Next dev origin. Demo-data mode is explicit in every payload (`mode: "demo-synthetic"`).

## Build order (prompt §11)
P1 shell/design system/theme/routing → P2 Home + components + demo data layer → P3 module pages → P4 drill-downs/scenarios/decisions → P5 Copilot → P6 data sources/reports/health → P7 responsive/a11y verification. Each phase is run and click-tested before expanding (this commit: P1–P6 functional core, P7 checks).

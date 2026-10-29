# CORTEXORA — Product Requirements Document (v0.1, Phase 1)

**Title:** The Intelligence Engine for Predictive Business Decisions
**Tagline:** Predict the Future. Optimize the Present. Engineer Business Growth.
**Domain (v1):** Retail / e-commerce. Architecture is domain-agnostic (entities are generic: customer, product, order, campaign).

## Problem
Business data is fragmented; dashboards explain the past, forecasts are not translated into actions.
CORTEXORA answers: What happened? Why? What next? What should we do? Did it work?

## Users
Executive (overview, decisions), Analyst (drill-down, metrics), Manager (approve/reject/defer recommendations).

## MVP (minimum end-to-end workflow) — THIS is the Phase 1–4 vertical slice
`sample data → ETL+validation → SQLite warehouse → metrics → forecast (vs baseline) → decision engine → approve/defer in UI → decision logged`
Acceptance: `python scripts/run_etl.py` succeeds with quality report; `pytest` green; `streamlit run app.py` shows KPIs computed from DB (no hard-coded charts); a recommendation can be approved and persists in `decisions` table.

## In scope (MVP→v1, in roadmap order)
1. Business Growth Intelligence (KPIs, trends, category/region/segment, period comparison, drill-down)
2. Demand Forecasting (weekly category forecast, chronological split, seasonal-naive baseline, MAE/RMSE/WAPE, stockout risk + reorder point)
3. Customer Intelligence (RFM segmentation; churn *risk heuristic labelled as heuristic until a validated model exists*)
4. Pricing scenario simulator (**assumption-based**, elasticity is a user input — never presented as estimated causal effect)
5. Marketing Performance (spend/ROAS/CAC on synthetic channel data; attributed ≠ incremental, stated in UI)
6. Decision Intelligence Engine (rule detectors over real module outputs; transparent priority score; human approval; audit log)
7. Data Quality & Monitoring (schema/missing/duplicate/range/freshness checks, visible warnings)

## Explicitly out of scope until data justifies them
MMM (needs ≥52 weekly obs/channel variation), causal claims, live competitor scraping, autonomous actions, RetainIQ integration (no repo access — revisit when provided; churn stays independent of any single model).

## Non-functional
No secrets in repo (.env), parameterized SQL, synthetic data labelled everywhere, reproducible seed, tests for metrics/forecast/quality/decision logic.

## Success criteria
See `docs/05_ROADMAP.md` per-phase acceptance criteria. A feature is done only when UI + calculation + test exist.

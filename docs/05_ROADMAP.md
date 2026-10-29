# Phased Plan & Acceptance Criteria
- **P1 Foundation (done this commit):** docs, schema, structure, app shell. ✅ app imports, ETL runs.
- **P2 Data Engineering (done):** idempotent ETL, validation, quality report, logging. ✅ rerun ETL → same row counts; bad row rejected in test.
- **P3 Core BI (done):** KPI/trend/category/region, period comparison, drill-down table + CSV download. ✅ metrics match hand-calculated test fixture.
- **P4 Predictive (done, on synthetic data):** weekly forecast vs seasonal-naive with WAPE; RFM; **validated churn classifier** (`cortexora/models/churn.py`, leakage-tested, baseline-compared, `docs/06_MODEL_CARD_CHURN.md`). ⏳ retrain on real data; RetainIQ review if repo provided.
- **P5 Optimization (done):** forecast-based reorder plan (95% service level), discount-effectiveness, break-even, constrained marketing budget optimizer (fitted power response curves, reliability-gated) — all feeding the Decision Engine (`docs/07_PHASE5_OPTIMIZATION.md`).
- **P6 Advanced (done):** Experimentation & Causal Lab (A/B + SRM + sample-size + DiD, known-effect-tested), Competitor Intelligence via validated user snapshots (no fake live feed), MMM **readiness gate** — fitting stays disabled until a joinable revenue outcome + controls exist (`docs/08_PHASE6_ADVANCED_ANALYTICS.md`).
- **P7 Decision Engine (done):** detectors, transparent priority, approve/reject/defer persisted, **outcome tracking**: owner + measurement period + due date, actual-outcome recording (approved-only, note required), expected-vs-actual calibration summary, audit-log export (`docs/09_PHASE7_DECISION_OUTCOMES.md`). ⏳ automatic outcome measurement when live post-decision data exists.
- **P8 Monitoring (done):** data-quality checks, pipeline run log, PSI drift, temporal model-performance monitoring, model-version metadata (`docs/10_PHASE8_MONITORING.md`).
- **P9–10 Polish/Deploy (done, except screenshots from a live deployment):** consistent navigation (12 pages incl. Reports + Settings & About), downloadable executive report, auto-bootstrapping app, Dockerfile + Streamlit theme, deployment & demo guide (`docs/11_DEPLOYMENT_AND_DEMO.md`). Screenshots intentionally not fabricated — capture from your deployment per docs/11.

## Risks & decisions needing resolution
1. No real dataset yet → all results are demo-only (mitigated by labelling; resolve by choosing UCI/Olist).
2. RetainIQ repo not provided → churn model deferred; architecture keeps it pluggable (`models/` boundary).
3. SQLite vs Postgres: SQLite for local MVP; schema kept portable; switch via CORTEXORA_DB/config in P10.
4. Elasticity cannot be estimated from synthetic observational data credibly → simulator is assumption-based by design.
5. Streamlit state for decision approval → persisted in SQLite `decisions`, not session state, for auditability.

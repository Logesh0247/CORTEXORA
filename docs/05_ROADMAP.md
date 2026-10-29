# Phased Plan & Acceptance Criteria
- **P1 Foundation (done this commit):** docs, schema, structure, app shell. ✅ app imports, ETL runs.
- **P2 Data Engineering (done):** idempotent ETL, validation, quality report, logging. ✅ rerun ETL → same row counts; bad row rejected in test.
- **P3 Core BI (done):** KPI/trend/category/region, period comparison, drill-down table + CSV download. ✅ metrics match hand-calculated test fixture.
- **P4 Predictive (done, on synthetic data):** weekly forecast vs seasonal-naive with WAPE; RFM; **validated churn classifier** (`cortexora/models/churn.py`, leakage-tested, baseline-compared, `docs/06_MODEL_CARD_CHURN.md`). ⏳ retrain on real data; RetainIQ review if repo provided.
- **P5 Optimization (partial):** reorder points, pricing assumption simulator, marketing CAC. ⏳ constrained budget optimizer.
- **P6 Advanced:** MMM/causal/competitor — **gated on real data**; UI states unavailability honestly rather than faking.
- **P7 Decision Engine (done, rule-based v1):** detectors, priority = impact×confidence×urgency (formula in code+UI), approve/reject/defer persisted. ⏳ outcome-vs-expected tracking after follow-up period.
- **P8 Monitoring (partial):** data-quality page. ⏳ drift (PSI) + model-performance tracking.
- **P9–10 Polish/Deploy:** screenshots, model cards, Streamlit Cloud config.

## Risks & decisions needing resolution
1. No real dataset yet → all results are demo-only (mitigated by labelling; resolve by choosing UCI/Olist).
2. RetainIQ repo not provided → churn model deferred; architecture keeps it pluggable (`models/` boundary).
3. SQLite vs Postgres: SQLite for local MVP; schema kept portable; switch via CORTEXORA_DB/config in P10.
4. Elasticity cannot be estimated from synthetic observational data credibly → simulator is assumption-based by design.
5. Streamlit state for decision approval → persisted in SQLite `decisions`, not session state, for auditability.

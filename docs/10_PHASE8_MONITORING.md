# Phase 8 — Reliability & Monitoring

## What was added
- **Pipeline run log** (`pipeline_runs` table): every ETL run records start/finish, status (`success` / `failed_quality_gate`), source, row counts, and quality-fail count. Visible on the Monitoring page.
- **Reliability fix:** the ETL previously dropped the `decisions` table on reload, which would have erased the Phase 7 audit history. Warehouse fact tables are rebuilt; `decisions` and `pipeline_runs` survive. Regression-tested (`test_etl_preserves_decisions_and_logs_run`).
- **Data drift (PSI):** Population Stability Index per numeric feature, reference-quantile bins — <0.10 stable, 0.10–0.25 moderate, >0.25 significant. Monitoring page compares the first 18 months vs the last 6.
- **Model-performance monitoring (temporal):** the churn model is trained on an earlier cohort and scored on a later, labelled cohort; PR-AUC delta beyond −0.05 flags degradation. Calibration (mean predicted vs observed churn) is shown alongside.
- **Model registry metadata:** `churn_evaluation.json` now carries model_version (`churn-v1`), trained_at, data_cutoff, label definition, and the synthetic-data warning.

## The distinction the UI enforces
Data drift ≠ prediction drift ≠ performance degradation. Drift means the world changed; only re-scoring on later labelled outcomes measures whether accuracy actually fell. A drift alert with stable later-period PR-AUC requires no retrain; degradation with no drift still does.

## Known limitations
- Static demo dataset: "current" periods are historical slices, so drift/performance are methodological demonstrations until a live feed lands.
- PSI is univariate; multivariate shift (correlations) needs additional checks (planned: correlation-matrix delta).
- No alerting channel (email/Slack) — statuses are in-app only.

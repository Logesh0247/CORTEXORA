# CORTEXORA
**The Intelligence Engine for Predictive Business Decisions**
*Predict the Future. Optimize the Present. Engineer Business Growth.*

An integrated retail decision-intelligence platform: ETL → warehouse → shared metrics → forecasting/RFM → rule-based Decision Engine with human approval and audit log.

> ⚠️ All data in this repo version is **synthetic** (seed=42), clearly labelled in the UI. No real business results are claimed.

## Quickstart
```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/run_etl.py     # generates sample data, validates, loads SQLite
.venv/bin/streamlit run app.py
.venv/bin/python -m pytest -q
```
## Implemented (verified)
Growth BI KPIs/trends/drill-down · weekly forecasting vs seasonal-naive baseline (MAE/RMSE/WAPE, chronological split) · RFM segments + validated churn classifier (leakage-tested, dummy-baseline comparison, model card in docs/06) · assumption-based pricing simulator + discount effectiveness + break-even · forecast-based reorder plan · constrained marketing budget optimizer (response curves, reliability-gated) · marketing CAC (ROAS honestly omitted — no attribution data) · stockout/reorder + churn-risk recommendations with approve/reject/defer, owner + measurement period, and expected-vs-actual outcome tracking persisted in SQLite · data-quality checks.

## Not yet (gated on real data — see docs/05_ROADMAP.md)
MMM, causal/experiment module, competitor radar, Postgres, RetainIQ integration (repo not yet provided).

## Docs
`docs/01_PRD.md` · `02_ARCHITECTURE.md` · `03_DATA_MODEL_AND_METRICS.md` · `04_DATASET_STRATEGY.md` · `05_ROADMAP.md`

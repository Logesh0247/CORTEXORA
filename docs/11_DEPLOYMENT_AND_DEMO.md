# Deployment & Demonstration Guide

## Option A — Streamlit Community Cloud (fastest portfolio path)
1. Push this repo to GitHub (done: Logesh0247/CORTEXORA).
2. share.streamlit.io → New app → repo `CORTEXORA`, branch `main` (merge the arena branch first), file `app.py`.
3. Deploy. On first boot the app **auto-bootstraps**: it generates the synthetic sample (seed=42) and builds the SQLite warehouse, then serves normally. No secrets are required for the demo.
4. Python version: 3.11. Dependencies come from `requirements.txt`.

## Option B — Docker
```bash
docker build -t cortexora .
docker run -p 8501:8501 cortexora   # open http://localhost:8501
```

## Option C — Local
```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/run_etl.py && .venv/bin/streamlit run app.py
.venv/bin/python -m pytest -q   # 34 tests
```

## Production notes (honest)
SQLite + bundled synthetic data is a demo configuration. Production needs: a licensed real dataset loaded through the same ETL (docs/04), CORTEXORA_DB pointing at Postgres, model retraining + re-evaluation (docs/06), and authenticated hosting — Streamlit's built-in auth or a reverse proxy. None of that is claimed as done.

## 10-minute demo script
1. **Home** — KPIs and 30-day comparison are computed live from the warehouse; note the synthetic-data banner.
2. **Demand Forecasting** — show the evaluation table first (model vs seasonal-naive baseline, chronological split), *then* the forecast. Scroll to the reorder plan.
3. **Customer Intelligence** — churn model metrics vs the dummy baseline; emphasise the leakage-tested label definition.
4. **Marketing Performance** — budget optimizer (+12.6% expected conversions on synthetic response curves), then the MMM readiness gate failing on purpose: "this is what honest tooling looks like."
5. **Experiments Lab** — run the default A/B test; change conversions to a null result and show the verdict change; show the sample-size planner.
6. **Decision Intelligence Engine** — Generate → approve the inventory recommendation with your name as owner → (optionally) record an outcome and watch the calibration panel.
7. **Monitoring** — pipeline run log, PSI drift (stable), temporal PR-AUC (no degradation).
8. **Reports** — download the executive report; every figure in it was computed in this session.

## Screenshots
Not committed: they must come from the deployed app to be truthful. Capture the 8 steps above from your deployment and place them in `docs/screenshots/` (referenced by the README when present).

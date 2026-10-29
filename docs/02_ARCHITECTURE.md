# Architecture & Data Flow

```
CSV/upload (raw, immutable) → pipelines.etl (validate→clean→load) → SQLite warehouse
  → analytics.metrics (single definition layer) → models.forecasting / RFM / pricing sim
  → decision_engine (detectors + scoring) → Streamlit UI → decisions table (audit + outcome tracking)
monitoring.quality runs at ETL time and is surfaced in the UI.
```

Layers & boundaries: UI never computes metrics; analytics never reads raw files; models consume analytics-ready frames; decision engine consumes module outputs only (dicts), never raw tables — so detectors are unit-testable without a DB.

Stack: Python, pandas/numpy, Plotly, scikit-learn/statsmodels (later phases), SQLite (Postgres-compatible schema design: no SQLite-only types in DDL intent), Streamlit, pytest. No microservices — unjustified at this scale.

Data flow (mermaid):
```mermaid
flowchart LR
 A[Raw CSVs data/raw]-->B[ETL validate+transform]|-->C[(SQLite: customers,products,orders,order_items,inventory,marketing_spend)]
 C-->D[metrics.py]-->E[Forecast/RFM/Pricing]
 E-->F[Decision Engine]-->G[Streamlit UI]-->H[(decisions audit log)]
 B-->I[Quality report]-->G
```
Config via env (`CORTEXORA_DB`, see .env.example). ETL is idempotent: tables are rebuilt from raw in a transaction; raw is never overwritten.

# Data Model & Metric Definitions

## Schema (grain stated; PK/FK)
| table | grain | keys |
|---|---|---|
| customers | 1 row/customer | customer_id PK |
| products | 1 row/product | product_id PK, category |
| orders | 1 row/order | order_id PK, customer_id FK, order_date, region, channel |
| order_items | 1 row/order×product | (order_id,product_id) PK, qty, unit_price, discount, unit_cost |
| inventory_snapshots | 1 row/product×date | product_id FK, stock_on_hand, lead_time_days |
| marketing_spend | 1 row/date×channel | date, channel PK, spend, clicks, conversions |
| decisions | 1 row/recommendation | recommendation_id PK, status, created_at, decided_at, expected/actual outcome |

**Grain warning:** revenue lives at order-item grain. Joining orders↔order_items and summing an order-level field duplicates it — metrics.py aggregates items first, then joins.

DDL: `database/schema.sql` (applied by ETL).

## Metric definitions (the ONLY definitions; all modules use analytics/metrics.py)
- **Revenue** = Σ qty × unit_price × (1−discount) over order_items (net of discount, excl. tax/shipping — none in data).
- **Profit** = Revenue − Σ qty × unit_cost. **Margin** = Profit / Revenue.
- **AOV** = Revenue / distinct orders. **Orders** = distinct order_id.
- **CAC** = channel spend / channel conversions (proxy for new customers; labelled proxy).
- **ROAS** = attributed revenue / spend. Synthetic data has no attribution join, so UI shows spend/conversions/CAC only and says so.
- **Churn risk (heuristic, not a model):** recency > 180 days → high. Replaced by a validated classifier in Phase 4 with precision/recall/ROC-AUC reported.
- **CLV (simple, documented):** avg order value × orders/year × 3-yr horizon. Assumption stated wherever shown.
- **Stockout risk:** forecast demand over lead time > stock_on_hand.
- **Reorder point** = forecast daily demand × lead_time + safety stock (z=1.65 × σ_daily × √lead_time, ~95% service level assumption).
- **Forecast error:** MAE, RMSE, WAPE = Σ|err| / Σ|actual|. Chronological split only.

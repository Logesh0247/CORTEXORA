# Model Card — Customer Churn Prediction (v1, Phase 4)

- **Business question:** Which previously-active customers will make no purchase in the next 90 days, so retention can be prioritised?
- **Target:** `churn=1` if a customer with ≥1 order on/before the cutoff has no order in (cutoff, cutoff+90d]. This is a *behavioural proxy* for churn (retail has no subscription cancellation event) — stated wherever predictions are shown.
- **Features (all computed strictly on/before cutoff):** recency_days, frequency, monetary, avg_order_value, avg_items_per_order, avg_discount, active_span_days, orders_last_30d/90d, tenure_days. Leakage test: `tests/test_churn.py::test_no_leakage_from_future_orders`.
- **Training data:** CORTEXORA warehouse (currently **synthetic demo data**, seed=42). Metrics below are therefore a pipeline validation, NOT real-world performance.
- **Validation:** stratified customer-level hold-out (30%), seed=42. Candidates: majority-class dummy baseline, logistic regression (scaled), random forest. Best selected by PR-AUC.
- **Metrics:** precision / recall / F1 / ROC-AUC / PR-AUC — reproduced by `scripts/train_churn.py`, stored in `cortexora/models/artifacts/churn_evaluation.json`.
- **Limitations:** synthetic-data patterns may not transfer; proxy label ≠ true churn; no demographics/external features; retrain + re-evaluate on real data before any business use. Feature importance explains the *model*, not causal drivers.
- **Use:** prioritise retention review. Never auto-act on a prediction.

"""Executive report generation (Phase 9). Every number in the report comes
from the same metric/model functions the UI uses — the report is a rendering
of computed results, never a hand-written narrative with invented figures."""
from __future__ import annotations
import pandas as pd
from cortexora.analytics.metrics import kpis, period_compare
from cortexora.models.forecasting import evaluate
from cortexora.decision_engine.engine import outcome_summary

def _fmt_money(x): return f"${x:,.0f}"

def generate_markdown_report(df, forecast_eval: dict | None, churn_rep: dict | None,
                             decisions: pd.DataFrame, generated_for: str = "All categories / full period") -> str:
    k = kpis(df); pc = period_compare(df).set_index("metric")
    lines = [
        "# CORTEXORA — Executive Report",
        "**The Intelligence Engine for Predictive Business Decisions**",
        f"_Scope: {generated_for} · Generated {pd.Timestamp.now():%Y-%m-%d %H:%M} · Data: synthetic demo (seed=42) unless stated otherwise_",
        "", "## Key performance indicators",
        f"- Revenue: {_fmt_money(k['revenue'])} · Profit: {_fmt_money(k['profit'])} · Margin: {k['margin']:.1%}",
        f"- Orders: {k['orders']:,} · Average order value: {_fmt_money(k['aov'])} · Units: {k['units']:,} · Customers: {k['customers']:,}",
        "", "## Last 30 days vs previous 30 days",
    ]
    for m in ["revenue", "profit", "orders", "aov"]:
        r = pc.loc[m]; lines.append(f"- {m}: {_fmt_money(r.current) if m != 'orders' else f'{r.current:,.0f}'} vs {_fmt_money(r.previous) if m != 'orders' else f'{r.previous:,.0f}'} ({r.change_pct:+.1f}%)")
    if forecast_eval:
        lines += ["", "## Demand forecast evaluation (chronological hold-out; lower is better)",
                  f"- Train ends {forecast_eval['train_end']} · test volume {forecast_eval['test_actual_total']:,.0f} units",
                  f"- Moving-average(4w): MAE {forecast_eval['moving_average_4w']['MAE']:.1f}, WAPE {forecast_eval['moving_average_4w']['WAPE']:.1%}",
                  f"- Seasonal-naive baseline: MAE {forecast_eval['seasonal_naive']['MAE']:.1f}, WAPE {forecast_eval['seasonal_naive']['WAPE']:.1%}"]
    if churn_rep:
        best = churn_rep["results"][churn_rep["best_model"]]
        lines += ["", "## Customer churn model",
                  f"- Model: {churn_rep['best_model']} ({churn_rep.get('model_version','churn-v1')}) · customers {churn_rep['n_customers']} · observed churn {churn_rep['churn_rate']:.1%}",
                  f"- Hold-out: precision {best['precision']:.2f}, recall {best['recall']:.2f}, F1 {best['f1']:.2f}, ROC-AUC {best['roc_auc']:.2f}, PR-AUC {best['pr_auc']:.2f}",
                  "- Label: no purchase within 90 days after cutoff (proxy). Synthetic-data metrics validate the pipeline, not real-world accuracy."]
    s = outcome_summary(decisions) if decisions is not None else {"measured": 0}
    pend = int((decisions.status == "pending").sum()) if decisions is not None and len(decisions) else 0
    lines += ["", "## Decision Intelligence",
              f"- Pending recommendations awaiting review: {pend}",
              f"- Measured decisions: {s['measured']}" + (f" · median |variance| vs expected {s['median_abs_variance_pct']:.1f}% · within ±20%: {s['within_20pct']:.0%}" if s["measured"] else " (no outcomes recorded yet — the engine does not invent results)"),
              "", "---",
              "_Definitions: docs/03_DATA_MODEL_AND_METRICS.md · Methods & limitations: docs/05–10. Forecasts are estimates, scenarios are assumption-based, recommendations require human approval._"]
    return "\n".join(lines)

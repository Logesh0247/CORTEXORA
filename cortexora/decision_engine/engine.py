"""Rule-based Decision Intelligence Engine v1. Consumes module outputs, not raw tables.
Priority = sqrt(expected_impact) x confidence x urgency — shown to the user, never hidden."""
import hashlib
import pandas as pd  # noqa: F401  (type hint)

def _rec(area, problem, action, evidence, impact, confidence, urgency):
    rid = "REC-" + hashlib.sha1(f"{area}{problem}{action}".encode()).hexdigest()[:8]
    return dict(recommendation_id=rid, area=area, problem=problem, action=action, evidence=evidence,
                expected_impact=float(impact), priority=round(float(impact)**0.5 * confidence * urgency, 2))

def stockout_recommendations(stock) -> list[dict]:
    """stock df: product_id, category, stock_on_hand, lead_time_days, forecast_daily, daily_sd"""
    out = []
    for r in stock.itertuples():
        need = r.forecast_daily * r.lead_time_days
        if r.stock_on_hand < need:
            reorder = need - r.stock_on_hand + 1.65 * r.daily_sd * (r.lead_time_days ** 0.5)
            out.append(_rec("Inventory", f"{r.category} product {int(r.product_id)} may stock out",
                f"Reorder ~{int(max(reorder,0))} units now", f"stock={int(r.stock_on_hand)}, lead-time demand={need:.0f}, lead={int(r.lead_time_days)}d",
                max(need - r.stock_on_hand, 0), 0.7, 1.0))
    return out

def churn_recommendations(rfm_df) -> list[dict]:
    mask = rfm_df.segment.astype(str) == "At risk"
    n = int(mask.sum()); val = float(rfm_df.loc[mask, "monetary"].sum())
    if n == 0: return []
    return [_rec("Customer", f"{n} customers At risk (recency 91-180d)", "Launch retention campaign to At risk segment",
                 f"At-risk historical revenue={val:,.0f} (observed fact; retention uplift is a scenario, not a prediction)", val, 0.5, 0.7)]

def persist(recs: list[dict], db_path) -> None:
    import sqlite3
    with sqlite3.connect(db_path) as con:
        con.executemany("INSERT OR IGNORE INTO decisions(recommendation_id,created_at,area,problem,action,evidence,expected_impact,priority) VALUES (?,?,?,?,?,?,?,?)",
                        [(r["recommendation_id"], pd.Timestamp.now().isoformat(), r["area"], r["problem"], r["action"], r["evidence"], r["expected_impact"], r["priority"]) for r in recs])

def set_status(rid: str, status: str, db_path) -> None:
    import sqlite3
    with sqlite3.connect(db_path) as con:
        con.execute("UPDATE decisions SET status=?, decided_at=? WHERE recommendation_id=?", (status, pd.Timestamp.now().isoformat(), rid))

def inventory_recommendations(plan) -> list[dict]:
    """From optimization.reorder_plan output (forecast-based, Phase 5)."""
    out = []
    for r in plan.itertuples():
        if r.stockout_risk == "High" and r.recommended_reorder_qty > 0:
            out.append(_rec("Inventory", f"{r.category} product {int(r.product_id)} forecast to stock out before replenishment",
                f"Reorder {int(r.recommended_reorder_qty)} units (est. cost ${r.estimated_order_cost:,.0f})",
                f"stock={int(r.stock_on_hand)}, forecast {r.forecast_daily:.1f}/day, lead={int(r.lead_time_days)}d, expected shortfall={r.expected_stockout_units_no_action:.0f} units (scenario, 95% service-level assumption)",
                getattr(r, "margin_at_risk", r.expected_stockout_units_no_action), 0.75, 1.0))
    return out

def budget_recommendation(opt: dict) -> list[dict]:
    if opt.get("expected_gain_pct", 0) <= 5: return []
    shifts = "; ".join(f"{c}: ${opt['current_allocation'][c]:,.0f}→${v:,.0f}/wk" for c, v in opt["allocation"].items())
    return [_rec("Marketing", "Current budget allocation is below the fitted optimum",
        f"Reallocate weekly budget: {shifts}",
        f"Fitted response curves estimate +{opt['expected_gain_pct']:.1f}% conversions at the same budget (model estimate on synthetic data, not incremental/causal)", 
        opt["expected_optimized"] - opt["expected_current"], 0.5, 0.6)]

def discount_recommendation(disc) -> list[dict]:
    if disc.empty: return []
    hi = disc.iloc[-1]; overall_margin = disc.profit.sum() / disc.revenue.sum()
    if hi.revenue_share > 0.10 and hi.margin < overall_margin / 2:
        return [_rec("Pricing", f"Deepest discount bucket ({hi.discount_bucket}) earns margin {hi.margin:.1%} vs {overall_margin:.1%} overall",
            "Review 20%+ discount policy: test reducing depth on low-margin products (run as experiment before claiming causality)",
            f"Observed association only: {hi.revenue_share:.1%} of revenue at avg discount {hi.avg_discount:.1%} — not a causal estimate",
            float(hi.profit), 0.45, 0.5)]
    return []

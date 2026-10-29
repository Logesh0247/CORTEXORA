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

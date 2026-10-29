"""Five-stage business intelligence over an UPLOADED dataset.

Runs on the enriched line-level frame produced from the user's own files
(never the demo warehouse) and answers, in order:

  1. UNDERSTAND   — what happened: KPIs, best/worst products & categories.
  2. DISCOVER     — why: recent-vs-prior profit bridge and the products,
                    categories, channels and segments that drove the change.
  3. PREDICT      — what next: 8-week forecast (baseline-scored), customers
                    at churn risk (labelled heuristic), fast-rising demand.
  4. TEST         — what-if: price, discount and inventory scenarios
                    recomputed from the uploaded lines (assumptions stated).
  5. RECOMMEND    — what to do: ranked actions, each with evidence, an
                    estimated impact and a measurement plan.

Honesty rules: every number is computed from the uploaded rows; anything the
file cannot support (e.g. stockout risk without stock levels, marketing
attribution without campaign data) is reported as unavailable with the reason,
never invented. Period comparisons use equal-length recent/prior windows.
"""
from __future__ import annotations
import numpy as np, pandas as pd


def _f(x) -> float:
    try: return float(x)
    except Exception: return 0.0


def _windows(d: pd.DataFrame):
    """Equal-length recent vs prior windows (second half vs first half)."""
    lo, hi = d["order_date"].min(), d["order_date"].max()
    mid = lo + (hi - lo) / 2
    return d[d["order_date"] > mid], d[d["order_date"] <= mid], mid


def _agg(d: pd.DataFrame) -> dict:
    rev = _f(d["revenue"].sum()); prof = _f(d["profit"].sum()); qty = _f(d["qty"].sum())
    return {"revenue": rev, "profit": prof, "margin": prof / rev if rev else 0.0,
            "units": qty, "orders": int(d["order_id"].nunique()),
            "avg_price": rev / qty if qty else 0.0,
            "avg_discount": _f(d["discount"].mean()) if "discount" in d else 0.0}


def _delta(cur: dict, prev: dict, key: str):
    p = prev.get(key, 0.0)
    return ((cur[key] / p - 1) * 100) if p else None


# ---------------------------------------------------------------- stage 1
def _understand(d: pd.DataFrame, rep: dict) -> dict:
    prod = (d.groupby(["product_name", "category"])
              .agg(revenue=("revenue", "sum"), profit=("profit", "sum"), units=("qty", "sum"),
                   orders=("order_id", "nunique")).reset_index())
    prod["margin"] = prod["profit"] / prod["revenue"].replace(0, np.nan)
    cat = (d.groupby("category").agg(revenue=("revenue", "sum"), profit=("profit", "sum")).reset_index())
    cat["margin"] = cat["profit"] / cat["revenue"].replace(0, np.nan)
    poor = prod[(prod["margin"] < 0.05) | (prod["profit"] < 0)].sort_values("profit")
    recent, prior, _ = _windows(d)
    rp = (recent.groupby("product_name")["revenue"].sum().rename("rev_recent")
          .to_frame().join(prior.groupby("product_name")["revenue"].sum().rename("rev_prior"), how="outer").fillna(0))
    rp["change_pct"] = np.where(rp["rev_prior"] > 0, (rp["rev_recent"] / rp["rev_prior"] - 1) * 100, np.nan)
    declining = rp[rp["change_pct"] < -20].sort_values("change_pct")
    j = lambda df, n=8: df.head(n).round(4).to_dict("records")
    return {
        "period": {"from": str(d["order_date"].min().date()), "to": str(d["order_date"].max().date()),
                   "rows": int(len(d)), "products": int(d["product_name"].nunique()),
                   "customers": int(d["customer_id"].nunique())},
        "top_products": j(prod.sort_values("revenue", ascending=False)),
        "best_margin_products": j(prod[prod["revenue"] > 0].sort_values("margin", ascending=False)),
        "poor_performers": j(poor.assign(reason=np.where(poor["profit"] < 0, "loses money (negative profit)",
                                                         "margin under 5%"))),
        "declining_products": [{"product_name": k, "change_pct": round(_f(v), 1)}
                               for k, v in declining["change_pct"].head(8).items()],
        "categories": j(cat.sort_values("revenue", ascending=False)),
        "worst_category": (cat.sort_values("margin").iloc[0].to_dict() if len(cat) else None),
    }


# ---------------------------------------------------------------- stage 2
def _discover(d: pd.DataFrame) -> dict:
    recent, prior, mid = _windows(d)
    cur, prev = _agg(recent), _agg(prior)
    bridge = {k: {"recent": round(cur[k], 2), "prior": round(prev[k], 2),
                  "change_pct": (round(_delta(cur, prev, k), 1) if _delta(cur, prev, k) is not None else None)}
              for k in ["revenue", "profit", "margin", "units", "avg_price", "avg_discount", "orders"]}

    def drivers(col):
        a = recent.groupby(col)["profit"].sum().rename("recent")
        b = prior.groupby(col)["profit"].sum().rename("prior")
        t = a.to_frame().join(b, how="outer").fillna(0); t["delta"] = t["recent"] - t["prior"]
        return [{"name": str(k), "profit_delta": round(_f(v), 2)}
                for k, v in t.sort_values("delta")["delta"].items()]

    findings = []
    if bridge["profit"]["change_pct"] is not None:
        pc = bridge["profit"]["change_pct"]
        if pc < -5:
            cause = []
            if (bridge["avg_discount"]["change_pct"] or 0) > 5: cause.append("average discount rose")
            if (bridge["avg_price"]["change_pct"] or 0) < -3: cause.append("average realised price fell")
            if (bridge["units"]["change_pct"] or 0) < -5: cause.append("units sold fell")
            if (bridge["margin"]["change_pct"] or 0) < -5 and not cause: cause.append("margin compressed (cost/price mix)")
            findings.append(f"Profit fell {abs(pc):.1f}% in the recent half" +
                            (f" — signals: {', '.join(cause)}." if cause else " — no single dominant signal; see drivers below."))
        elif pc > 5:
            findings.append(f"Profit grew {pc:.1f}% in the recent half — the drivers below show what to scale.")
    seg = _segments(d)
    if seg["at_risk_share"] and seg["at_risk_share"] > 0.15:
        findings.append(f"{seg['at_risk_share']*100:.0f}% of customers show no purchase in 90+ days "
                        f"(${seg['at_risk_monetary']:,.0f} of historical revenue) — retention is a lever.")
    if "channel" in d and d["channel"].nunique() > 1 and (d["channel"] != "Unknown").any():
        ch = d.groupby("channel").agg(revenue=("revenue", "sum"), profit=("profit", "sum"))
        ch["margin"] = ch["profit"] / ch["revenue"]
        worst = ch.sort_values("margin").index[0]
        findings.append(f"Channel '{worst}' has the thinnest margin ({ch.loc[worst, 'margin']*100:.1f}%).")
    else:
        findings.append("Marketing campaigns cannot be assessed — the file has no campaign/marketing columns "
                        "(channel here is a sales channel, not campaign attribution).")
    return {"split_date": str(pd.Timestamp(mid).date()), "bridge": bridge,
            "profit_drivers_products": drivers("product_name")[:6],
            "profit_drivers_categories": drivers("category")[:5],
            "findings": findings, "segments": seg}


def _segments(d: pd.DataFrame) -> dict:
    ref = d["order_date"].max()
    g = d.groupby("customer_id").agg(last=("order_date", "max"), orders=("order_id", "nunique"),
                                     monetary=("revenue", "sum"))
    g["recency_days"] = (ref - g["last"]).dt.days
    n = max(1, len(g))
    return {"customers": int(len(g)),
            "repeat_share": round(_f((g["orders"] > 1).mean()), 3),
            "at_risk": int((g["recency_days"] > 90).sum()),
            "at_risk_share": round(_f((g["recency_days"] > 90).mean()), 3),
            "at_risk_monetary": round(_f(g.loc[g["recency_days"] > 90, "monetary"].sum()), 2),
            "top_at_risk": [{"customer_id": int(k) if str(k).isdigit() else str(k),
                             "days_since_last_order": int(v["recency_days"]),
                             "historical_revenue": round(_f(v["monetary"]), 2),
                             "orders": int(v["orders"])}
                            for k, v in g[g["recency_days"] > 90].sort_values("monetary", ascending=False).head(8).iterrows()]}


# ---------------------------------------------------------------- stage 3
def _predict(d: pd.DataFrame, forecast_block: dict) -> dict:
    seg = _segments(d)
    recent, prior, _ = _windows(d)
    prod_recent = recent.groupby("product_name")["qty"].sum().rename("recent_units")
    prod_prior = prior.groupby("product_name")["qty"].sum().rename("prior_units")
    t = prod_recent.to_frame().join(prod_prior, how="outer").fillna(0)
    t["growth_pct"] = np.where(t["prior_units"] > 0, (t["recent_units"] / t["prior_units"] - 1) * 100, np.nan)
    rising = t[t["growth_pct"] > 30].sort_values("growth_pct", ascending=False).head(6)
    return {"forecast": forecast_block,
            "churn_risk": {"method": "recency heuristic (>90 days inactive) — labelled heuristic, "
                                     "not a trained churn model",
                           **{k: seg[k] for k in ["customers", "at_risk", "at_risk_share", "at_risk_monetary"]},
                           "top_at_risk": seg["top_at_risk"]},
            "demand_rising": [{"product_name": str(k), "growth_pct": round(_f(v), 1)}
                              for k, v in rising["growth_pct"].items()],
            "stockout_risk": {"available": False,
                              "reason": "Stock levels were not in the uploaded file(s) (inventory is "
                                        "unknown, treated as 0 in the warehouse schema), so stockout risk "
                                        "cannot be computed honestly. Upload a file with a stock/inventory "
                                        "column per product to enable it. Demand-rising products above are "
                                        "the ones to check first."}}


# ---------------------------------------------------------------- stage 4
def _test_decisions(d: pd.DataFrame, forecast_block: dict) -> dict:
    rev, prof = _f(d["revenue"].sum()), _f(d["profit"].sum())
    qty, disc = _f(d["qty"].sum()), (_f(d["discount"].mean()) if "discount" in d else 0.0)
    scenarios = []
    for change in (0.05, -0.05):
        elasticity = -1.2  # stated assumption, same as the Pricing module
        unit_factor = 1 + elasticity * change
        new_rev = rev * (1 + change) * unit_factor
        new_prof = new_rev - (rev - prof) * unit_factor  # product costs scale with units sold
        scenarios.append({"name": f"Price {'+' if change > 0 else ''}{change*100:.0f}% (all products)",
                          "assumption": "price elasticity −1.2 (assumption — not estimated from this file)",
                          "revenue_change_pct": round((new_rev / rev - 1) * 100, 1) if rev else None,
                          "projected_revenue": round(new_rev, 2), "projected_profit": round(new_prof, 2)})
    if disc > 0.005:
        # exact recompute: halve every discount on the uploaded lines
        sim_rev = _f((d["qty"] * d["unit_price"] * (1 - d["discount"] / 2)).sum())
        sim_prof = sim_rev - _f((d["qty"] * d["unit_cost"]).sum())
        scenarios.append({"name": "Halve all discounts",
                          "assumption": "exact recomputation on uploaded lines; assumes volumes unchanged (optimistic bound)",
                          "revenue_change_pct": round((sim_rev / rev - 1) * 100, 1) if rev else None,
                          "projected_revenue": round(sim_rev, 2), "projected_profit": round(sim_prof, 2)})
    else:
        scenarios.append({"name": "Halve all discounts", "assumption": "not applicable",
                          "revenue_change_pct": None, "projected_revenue": None, "projected_profit": None,
                          "note": "No discount column (or all zeros) in the uploaded data."})
    inv = {"name": "Order 4 weeks of forecast demand", "available": bool(forecast_block.get("available"))}
    if forecast_block.get("available") and forecast_block.get("predicted_units_8w"):
        weekly_units = forecast_block["predicted_units_8w"] / 8
        avg_cost = _f((d["qty"] * d["unit_cost"]).sum() / qty) if qty else 0.0
        inv.update(units_to_cover_4w=round(weekly_units * 4), estimated_cost=round(weekly_units * 4 * avg_cost, 2),
                   assumption="4 weeks at the forecast weekly rate; unit cost = weighted average from this file")
    else:
        inv["note"] = "Needs an available forecast (≥24 weekly periods)."
    scenarios.append(inv)
    scenarios.append({"name": "Increase marketing spend",
                      "note": "Cannot be simulated honestly: the uploaded file(s) contain no marketing "
                              "spend/response data. Upload spend by channel/date and CORTEXORA can fit "
                              "response curves — correlation alone would not justify a causal claim."})
    return {"scenarios": scenarios,
            "note": "Scenarios are what-if computations under the stated assumptions — not predictions or guarantees."}


# ---------------------------------------------------------------- stage 5
def _recommend(understand: dict, discover: dict, predict: dict, rep: dict) -> list[dict]:
    recs = []
    for p in understand["poor_performers"][:3]:
        impact = abs(_f(p["profit"])) + _f(p["revenue"]) * 0.02
        recs.append({"action": f"Fix or delist '{p['product_name']}'",
                     "evidence": f"{p['reason']}: margin {(_f(p['margin'])*100):.1f}% on ${_f(p['revenue']):,.0f} revenue, profit ${_f(p['profit']):,.0f}.",
                     "expected_impact": round(impact, 2), "impact_basis": "loss removed + 2% of its revenue recovered (estimate)",
                     "measure": "Track this product's weekly margin and profit for 28 days after the change; success = margin ≥ 10%."})
    for name in understand["declining_products"][:2]:
        recs.append({"action": f"Investigate declining product '{name['product_name']}'",
                     "evidence": f"Revenue fell {abs(name['change_pct']):.0f}% between the two halves of the uploaded history.",
                     "expected_impact": 0.0, "impact_basis": "investigation first — impact quantified once the cause is known",
                     "measure": "Compare weekly units and average price for this product over the next 28 days vs the prior 28."})
    ch = predict["churn_risk"]
    if ch["at_risk"] and ch["at_risk_monetary"] > 0:
        recs.append({"action": f"Win back {ch['at_risk']} inactive customers (90+ days)",
                     "evidence": f"They represent ${ch['at_risk_monetary']:,.0f} of historical revenue; top names are listed in Predict.",
                     "expected_impact": round(ch["at_risk_monetary"] * 0.05, 2),
                     "impact_basis": "5% of their historical revenue reactivated (planning estimate, not a promise)",
                     "measure": "Track reactivated customers and their revenue for 90 days; success = ≥5% return."})
    drv = discover["profit_drivers_products"]
    if drv and drv[0]["profit_delta"] < 0:
        recs.append({"action": f"Root-cause the profit drop in '{drv[0]['name']}'",
                     "evidence": f"Largest profit drag between halves: ${drv[0]['profit_delta']:,.0f}.",
                     "expected_impact": round(abs(drv[0]["profit_delta"]) * 0.5, 2),
                     "impact_basis": "recovering half the observed drag (estimate)",
                     "measure": "Track this product's weekly profit for 28 days; success = drag halved."})
    for name in predict["demand_rising"][:2]:
        recs.append({"action": f"Secure supply for fast-rising '{name['product_name']}'",
                     "evidence": f"Demand grew {name['growth_pct']:.0f}% between halves; a stockout here costs the most momentum.",
                     "expected_impact": 0.0, "impact_basis": "risk avoidance — quantify once stock levels are uploaded",
                     "measure": "Track weekly units and any out-of-stock days for 30 days (needs stock data)."})
    if rep.get("cost_is_assumption"):
        recs.append({"action": "Upload a cost column to replace the profit assumption",
                     "evidence": "Profit in this analysis uses the labelled 55%-of-price cost assumption.",
                     "expected_impact": 0.0, "impact_basis": "data-quality action — makes every profit figure exact",
                     "measure": "Re-run this analysis with unit_cost included; profit figures become observed, not estimated."})
    recs.sort(key=lambda r: -r["expected_impact"])
    for i, r in enumerate(recs, 1):
        r["priority"] = i
    return recs[:6]


# ------------------------------------------------------------------- main
def business_intelligence(d: pd.DataFrame, report: dict, forecast_block: dict) -> dict:
    """Run all five stages on an enriched uploaded-data frame."""
    understand = _understand(d, report)
    discover = _discover(d)
    predict = _predict(d, forecast_block)
    tests = _test_decisions(d, forecast_block)
    return {"understand": understand, "discover": discover, "predict": predict,
            "test_decisions": tests, "recommendations": _recommend(understand, discover, predict, report),
            "note": "Computed from your uploaded file(s) only. Estimates and heuristics are labelled; "
                    "unavailable analyses state why instead of inventing results."}

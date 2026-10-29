"""CORTEXORA AI Assistant — a data-grounded, offline assistant.

It answers from the *actual computed analytics* in this app (metrics layer,
forecasts, churn artifact, reorder plan, marketing optimiser, decision log),
never from invented figures. It is a transparent rule/NLU assistant that runs
fully offline — no external LLM API, no key, no data leaves the machine.
If it cannot answer from the available data, it says so and points to the
module that can. See docs/12_AI_ASSISTANT.md.
"""
from __future__ import annotations
import re
import pandas as pd

DEFINITIONS = {
    "revenue": "Revenue = Σ qty × unit_price × (1 − discount) over order items (net of discount). Defined once in the shared metrics layer (docs/03).",
    "profit": "Profit = revenue − Σ qty × unit_cost. Margin = profit ÷ revenue.",
    "margin": "Margin = profit ÷ revenue, where profit = revenue − product cost.",
    "aov": "AOV (average order value) = revenue ÷ number of distinct orders.",
    "cac": "CAC here is a proxy = marketing spend ÷ conversions. There is no attribution join in this data, so ROAS is intentionally not shown — attributed revenue is not incremental revenue.",
    "roas": "ROAS = attributed revenue ÷ spend. CORTEXORA does not display it yet: orders carry no channel attribution, so any ROAS would be fabricated.",
    "churn": "Churn (label) = a customer with no purchase in the 90 days after the model cutoff. It is a behavioural proxy — retail has no cancellation event.",
    "clv": "CLV (simple) = average monetary value per year × a 3-year horizon, computed in RFM. The assumptions are stated wherever it appears.",
    "wape": "WAPE = Σ|forecast error| ÷ Σ|actual|. Lower is better; the app always compares it against a seasonal-naive baseline on a chronological hold-out.",
    "psi": "PSI (Population Stability Index) measures distribution shift: <0.10 stable, 0.10–0.25 moderate, >0.25 significant. Drift alone does not prove a model degraded.",
    "stockout": "A product is stockout-risk 'High' when forecast demand over its lead time exceeds stock on hand (reorder plan: 95% service-level assumption).",
}
NAV_HINTS = [
    (["forecast", "demand", "inventory", "reorder", "stock"], "Demand Forecasting"),
    (["churn", "customer", "retention", "rfm", "segment"], "Customer Intelligence"),
    (["price", "pricing", "discount", "break-even", "breakeven", "margin"], "Pricing & Profit Optimization"),
    (["marketing", "budget", "channel", "cac", "campaign", "mmm"], "Marketing Performance"),
    (["experiment", "a/b", "ab test", "causal", "significance", "sample size"], "Experiments & Causal Lab"),
    (["competitor", "rival", "market price"], "Competitor Intelligence"),
    (["recommend", "decision", "approve", "outcome"], "Decision Intelligence Engine"),
    (["quality", "drift", "monitor", "pipeline", "trust"], "Data Quality & Monitoring"),
    (["report", "export", "download"], "Reports"),
    (["growth", "revenue trend", "sales trend"], "Business Growth"),
]

def _money(x): return f"${x:,.0f}"
def _find(word_list, q):
    return next((w for w in word_list if w in q), None)

def answer_question(question: str, ctx: dict) -> dict:
    """ctx keys: df (enriched line items incl. category/region/channel), products,
    mkt, decisions (DataFrame), churn_rep (dict|None), inv (DataFrame)."""
    q = (question or "").strip().lower()
    df = ctx.get("df"); products = ctx.get("products")
    out = dict(text="", table=None, navigate=None)
    if not q:
        out["text"] = "Ask me about revenue, forecasts, churn, stockouts, marketing, decisions — or type **help**."
        return out
    if q in {"hi", "hello", "hey"} or q.startswith(("hi ", "hello ")):
        out["text"] = "Hello! I'm the CORTEXORA Assistant. I answer from this app's live computed data (synthetic demo data, seed=42). Try: *“What is our revenue and profit?”*, *“Forecast Electronics demand”*, *“Which products may stock out?”*, *“What should we do next?”*"
        return out
    if "help" in q or "what can you" in q or "capabilit" in q:
        out["text"] = ("I can help with:\n"
                        "- **Performance:** “What is our revenue/profit/margin?” · “Top category / product / region?”\n"
                        "- **Why:** “Why did revenue change?” (last 30d vs prior 30d, by category)\n"
                        "- **Future:** “Forecast Electronics demand” · “Which customers are at churn risk?”\n"
                        "- **Actions:** “Which products may stock out?” · “Best marketing channel?” · “What should we do next?”\n"
                        "- **Pricing:** “What if I raise Electronics Product 1 price by 10%?” (assumption-based scenario)\n"
                        "- **Concepts:** “What is WAPE / CAC / churn / PSI?”\n"
                        "- **Navigation:** “Where can I run an A/B test?”\n"
                        "Everything I quote is computed from the current warehouse — and I'll say so when the data can't answer.")
        return out
    # --- definitions (only for genuinely definitional phrasing, so
    # "what is our revenue?" still routes to the KPI answer) ---
    for key, text in DEFINITIONS.items():
        if key in q and (any(w in q for w in ["define", "meaning", "mean by", "explain"]) or len(q.split()) <= 5):
            out["text"] = text; return out
    # --- navigation help ---
    if any(w in q for w in ["where", "how do i", "how to", "open", "go to", "find"]):
        for words, page in NAV_HINTS:
            if _find(words, q):
                out["text"] = f"That's in **{page}** — use the button below or the sidebar."; out["navigate"] = page; return out
    # --- decisions / recommendations ---
    if any(w in q for w in ["recommend", "what should we do", "next action", "decision", "pending"]):
        dec = ctx.get("decisions")
        if dec is None or not len(dec):
            out["text"] = "There are no recommendations in the decision log yet. Open the Decision Intelligence Engine and click **Generate recommendations** — it builds them from the forecast, inventory, marketing and customer modules."
            out["navigate"] = "Decision Intelligence Engine"; return out
        pend = dec[dec.status == "pending"].sort_values("priority", ascending=False)
        counts = dec.status.value_counts().to_dict()
        lines = [f"Decision pipeline: " + ", ".join(f"{k} {v}" for k, v in counts.items()) + "."]
        if len(pend):
            r = pend.iloc[0]
            lines.append(f"Top pending: **{r.recommendation_id} ({r.area})** — {r.problem} → {r.action}. Evidence: {r.evidence}")
            out["table"] = pend[["recommendation_id", "area", "problem", "action", "priority"]].head(5)
        lines.append("Approve/reject/defer them in the Decision Engine; outcomes are tracked against expectations there.")
        out["text"] = "\n\n".join(lines); out["navigate"] = "Decision Intelligence Engine"; return out
    # --- inventory / stockouts ---
    if any(w in q for w in ["stock", "reorder", "inventory"]):
        from cortexora.optimization.optimize import daily_demand_stats, reorder_plan
        if df is None or ctx.get("inv") is None:
            out["text"] = "I need the warehouse inventory snapshot for that — open Demand Forecasting."; out["navigate"] = "Demand Forecasting"; return out
        stats = daily_demand_stats(df)
        stock = ctx["inv"].merge(products[["product_id", "category", "unit_cost", "list_price"]], on="product_id").merge(stats, on="product_id", how="left").fillna(0)
        plan = reorder_plan(stock)
        high = plan[plan.stockout_risk == "High"]
        out["text"] = (f"**{len(high)} product(s) at high stockout risk** under the forecast-based plan (95% service level, margin-at-risk ranked in the table). "
                        f"Total recommended reorder: {int(plan.recommended_reorder_qty.sum()):,} units ≈ ${_money(plan.estimated_order_cost.sum()) if False else f'{plan.estimated_order_cost.sum():,.0f}'} at unit cost."
                        if len(high) else "No products are at high stockout risk right now under the forecast-based plan (95% service level).")
        if len(high): out["table"] = high[["product_id", "category", "stock_on_hand", "forecast_daily", "lead_time_days", "recommended_reorder_qty", "estimated_order_cost"]].head(10)
        out["navigate"] = "Demand Forecasting"; return out
    # --- forecast ---
    if any(w in q for w in ["forecast", "demand next", "future demand", "predict demand", "will sell"]):
        from cortexora.models.forecasting import weekly_series, forecast_next, evaluate
        cats = sorted(df.category.unique()) if df is not None else []
        cat = next((c for c in cats if c.lower() in q), None) or (cats[0] if cats else None)
        if cat is None: out["text"] = "No category data is loaded yet."; return out
        s = weekly_series(df, cat, products); fc = forecast_next(s, 8); ev = evaluate(s)
        out["text"] = (f"**{cat} demand forecast (next 8 weeks):** ≈ {fc.forecast.sum():,.0f} units total, about {fc.forecast.mean():,.0f}/week. "
                        f"Measured accuracy on a chronological hold-out: model WAPE {ev['moving_average_4w']['WAPE']:.1%} vs seasonal-naive {ev['seasonal_naive']['WAPE']:.1%} — "
                        + ("the model beats the simple baseline on this data." if ev['moving_average_4w']['WAPE'] < ev['seasonal_naive']['WAPE'] else "**the model does not beat the baseline here, so treat this outlook cautiously.**"))
        out["table"] = fc.assign(week=fc.week.dt.date); out["navigate"] = "Demand Forecasting"; return out
    # --- churn / customers ---
    if any(w in q for w in ["churn", "retention", "at risk", "losing customers"]):
        from cortexora.models.forecasting import rfm
        r = rfm(ctx["orders"], ctx["items"]) if ctx.get("orders") is not None else None
        rep = ctx.get("churn_rep")
        seg = r.segment.astype(str) if r is not None else pd.Series(dtype=str)
        lines = [f"Customer segments right now: **{int((seg=='Active').sum())} active, {int((seg=='At risk').sum())} at risk (91–180d), {int(seg.str.startswith('Churned').sum())} churned-heuristic (>180d)**."]
        if rep:
            best = rep["results"][rep["best_model"]]
            lines.append(f"Validated churn model ({rep['best_model']}): ROC-AUC {best['roc_auc']:.2f}, PR-AUC {best['pr_auc']:.2f} vs baseline PR-AUC {rep['results']['baseline_majority']['pr_auc']:.2f}; observed churn {rep['churn_rate']:.1%}. The ranked risk worklist is in Customer Intelligence.")
        lines.append("Note: these are model/heuristic risk signals on synthetic data — prioritisation aids, not verdicts on customers.")
        out["text"] = "\n\n".join(lines); out["navigate"] = "Customer Intelligence"; return out
    # --- marketing ---
    if any(w in q for w in ["marketing", "channel", "cac", "budget", "campaign", "advertis"]):
        from cortexora.analytics.metrics import marketing_metrics
        from cortexora.optimization.optimize import optimize_budget
        mm = marketing_metrics(ctx["mkt"]); best_ch = mm.loc[mm.cac_proxy.idxmin()]
        opt = optimize_budget(ctx["mkt"])
        out["text"] = (f"Best CAC (proxy = spend/conversions): **{best_ch.channel}** at ${best_ch.cac_proxy:,.2f}. Blended CAC is ${mm.spend.sum()/max(mm.conversions.sum(),1):,.2f} on ${mm.spend.sum():,.0f} total spend. "
                        f"Fitted response curves suggest reallocating the same weekly budget could change conversions by **{opt.get('expected_gain_pct',0):+.1f}%** (associational scenario, not causal incrementality). MMM is readiness-gated — details on the Marketing page.")
        out["table"] = mm; out["navigate"] = "Marketing Performance"; return out
    # --- pricing scenario ---
    if "price" in q and "%" in q and products is not None:
        mnum = re.search(r"(\d+(?:\.\d+)?)\s*%", q)
        match = next((r for r in products.itertuples() if r.product_name.lower() in q), None)
        if mnum and match is not None:
            from cortexora.analytics.metrics import enrich
            chg = float(mnum.group(1)) * (-1 if any(w in q for w in ["decrease", "reduce", "lower", "cut", "drop"]) else 1)
            elas = -1.2
            items_ = ctx["items"]; sold = items_[items_.product_id == match.product_id]
            base_q, base_rev = sold.qty.sum(), (sold.qty * sold.unit_price * (1 - sold.discount)).sum()
            new_rev = base_q * (1 + elas * chg / 100) * match.list_price * (1 + chg / 100)
            out["text"] = (f"Scenario (assumption-based, elasticity {elas}): raising **{match.product_name}** price by {chg:+.0f}% "
                            f"({'$'}{match.list_price:,.2f} → {'$'}{match.list_price*(1+chg/100):,.2f}) gives revenue ≈ ${new_rev:,.0f} vs observed ${base_rev:,.0f} ({new_rev/base_rev-1:+.1%}). "
                            "This is **not** a causal estimate — test price changes in the Experiments Lab before believing them.")
            out["navigate"] = "Pricing & Profit Optimization"; return out
    # --- why did it change ---
    if q.startswith("why") or "why did" in q:
        from cortexora.analytics.metrics import period_compare
        pc = period_compare(df).set_index("metric"); rev = pc.loc["revenue"]
        end = df.order_date.max(); cur = df[df.order_date > end - pd.Timedelta(days=30)]; prev = df[(df.order_date <= end - pd.Timedelta(days=30)) & (df.order_date > end - pd.Timedelta(days=60))]
        by = pd.DataFrame(dict(current=cur.groupby("category").revenue.sum(), previous=prev.groupby("category").revenue.sum())).fillna(0)
        by["change"] = by.current - by.previous; by = by.sort_values("change")
        worst, best_ = by.index[0], by.index[-1]
        out["text"] = (f"Revenue {rev.change_pct:+.1f}% in the last 30 days vs the prior 30 ({_money(rev.current)} vs {_money(rev.previous)}). "
                        f"Biggest drag: **{worst}** ({_money(by.loc[worst,'change'])}). Biggest lift: **{best_}** ({_money(by.loc[best_,'change'])}). "
                        "This is a descriptive decomposition of what changed — not proof of *why* in a causal sense.")
        out["table"] = by.reset_index(); out["navigate"] = "Business Growth"; return out
    # --- top / best ---
    if any(w in q for w in ["top", "best", "highest", "biggest", "most"]) and df is not None:
        if "product" in q:
            g = df.merge(products[["product_id", "product_name"]], on="product_id").groupby("product_name").revenue.sum().sort_values(ascending=False)
            out["text"] = f"Top product by revenue: **{g.index[0]}** ({_money(g.iloc[0])}), of {_money(g.sum())} total in scope."; out["table"] = g.head(10).rename("revenue").reset_index(); out["navigate"] = "Business Growth"; return out
        dim = "region" if "region" in q else "channel" if "channel" in q else "category"
        g = df.groupby(dim).revenue.sum().sort_values(ascending=False)
        out["text"] = f"Top {dim}: **{g.index[0]}** with {_money(g.iloc[0])} ({g.iloc[0]/g.sum():.0%} of revenue in scope). Full breakdown:"; out["table"] = g.rename("revenue").reset_index(); out["navigate"] = "Business Growth"; return out
    # --- headline metrics / data facts ---
    if any(w in q for w in ["revenue", "profit", "margin", "sales", "aov", "orders", "how is the business", "performance", "kpi"]):
        from cortexora.analytics.metrics import kpis, period_compare
        k = kpis(df); pc = period_compare(df).set_index("metric")
        out["text"] = (f"Current picture (all data in scope, synthetic demo): **Revenue {_money(k['revenue'])} · Profit {_money(k['profit'])} · Margin {k['margin']:.1%} · Orders {k['orders']:,} · AOV ${k['aov']:,.2f} · Customers {k['customers']:,}**. "
                        f"Last 30d vs prior 30d: revenue {pc.loc['revenue','change_pct']:+.1f}%, profit {pc.loc['profit','change_pct']:+.1f}%, orders {pc.loc['orders','change_pct']:+.1f}%. "
                        "Ask *“why did revenue change?”* for the category decomposition.")
        out["table"] = df.groupby("category").agg(revenue=("revenue", "sum"), profit=("profit", "sum"), orders=("order_id", "nunique")).assign(margin=lambda x: x.profit / x.revenue).reset_index()
        out["navigate"] = "Business Growth"; return out
    if any(w in q for w in ["data quality", "fresh", "trust", "how much data", "records", "dataset"]):
        out["text"] = (f"The warehouse holds {len(df):,} order lines across {df.order_id.nunique():,} orders, {df.customer_id.nunique():,} customers and {df.product_id.nunique()} products, "
                        f"{df.order_date.min().date()} → {df.order_date.max().date()}. It is **synthetic demo data**; quality checks, pipeline runs and drift live in Data Quality & Monitoring.")
        out["navigate"] = "Data Quality & Monitoring"; return out
    if any(w in q for w in ["experiment", "a/b", "sample size", "significant"]):
        out["text"] = ("The Experiments & Causal Lab analyses A/B tests (effect, 95% CI, Cohen's h, SRM check), plans sample sizes, and runs difference-in-differences. "
                        "Rule of thumb it enforces: fix your sample size *before* launching, and never claim causality without randomisation or a defensible quasi-experimental design.")
        out["navigate"] = "Experiments & Causal Lab"; return out
    if any(w in q for w in ["competitor", "rival"]):
        out["text"] = "Competitor Intelligence works from price snapshots **you** supply (validated CSV with source + timestamp) — CORTEXORA has no live competitor feed and doesn't pretend to. It flags competitors undercutting us by ≥5%."
        out["navigate"] = "Competitor Intelligence"; return out
    out["text"] = ("I couldn't map that to the data I can compute. I answer best from live analytics — try one of: "
                    "*“What is our revenue and profit?”* · *“Why did revenue change?”* · *“Forecast Apparel demand”* · "
                    "*“Which products may stock out?”* · *“Best marketing channel?”* · *“What should we do next?”* · *“What is WAPE?”* — or type **help**.")
    return out

SUGGESTIONS = ["What is our revenue and profit?", "Why did revenue change?", "Forecast Electronics demand",
               "Which products may stock out?", "Which customers are at churn risk?", "Best marketing channel?",
               "What should we do next?", "What is WAPE?"]

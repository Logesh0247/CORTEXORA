"""CORTEXORA — The Intelligence Engine for Predictive Business Decisions.
Run: streamlit run app.py  (run scripts/run_etl.py first)"""
import sqlite3
import pandas as pd, plotly.express as px, streamlit as st
from cortexora.config import DB_PATH
from cortexora.pipelines.etl import load_table
from cortexora.analytics.metrics import enrich, kpis, period_compare, marketing_metrics
from cortexora.models.forecasting import weekly_series, evaluate, forecast_next, rfm
from cortexora.decision_engine.engine import stockout_recommendations, churn_recommendations, inventory_recommendations, budget_recommendation, discount_recommendation, persist, set_status
from cortexora.optimization.optimize import reorder_plan, daily_demand_stats, discount_effectiveness, breakeven_units, optimize_budget

st.set_page_config(page_title="CORTEXORA", layout="wide")
if not DB_PATH.exists():
    st.error("Database not found. Run: `python scripts/run_etl.py`"); st.stop()
orders, items, products, inv, mkt = (load_table(t) for t in ["orders","order_items","products","inventory_snapshots","marketing_spend"])
df = enrich(orders, items).merge(products[["product_id","category"]], on="product_id")

st.sidebar.title("🧠 CORTEXORA")
page = st.sidebar.radio("Module", ["Home / Executive Overview","Business Growth","Demand Forecasting","Pricing Simulator","Customer Intelligence","Marketing Performance","Decision Intelligence Engine","Data Quality & Monitoring"])
st.sidebar.warning("⚠️ Synthetic demo data (seed=42) — not real business results.")
cats = st.sidebar.multiselect("Category", sorted(df.category.unique()), default=sorted(df.category.unique()))
dmin, dmax = st.sidebar.date_input("Date range", [df.order_date.min().date(), df.order_date.max().date()])
f = df[df.category.isin(cats) & df.order_date.between(pd.Timestamp(dmin), pd.Timestamp(dmax))]
st.caption("CORTEXORA · The Intelligence Engine for Predictive Business Decisions · Predict the Future. Optimize the Present. Engineer Business Growth.")

if page == "Home / Executive Overview":
    st.title("Executive Overview"); k = kpis(f)
    c = st.columns(5)
    for col, (label, val) in zip(c, [("Revenue",f"${k['revenue']:,.0f}"),("Profit",f"${k['profit']:,.0f}"),("Margin",f"{k['margin']:.1%}"),("Orders",f"{k['orders']:,}"),("AOV",f"${k['aov']:,.2f}")]):
        col.metric(label, val)
    st.plotly_chart(px.line(f.groupby("order_date").revenue.sum().reset_index(), x="order_date", y="revenue", title="Revenue trend (actuals)"), use_container_width=True)
    st.subheader("Last 30 days vs previous 30 days"); st.dataframe(period_compare(f), use_container_width=True)
    with sqlite3.connect(DB_PATH) as con: dec = pd.read_sql("SELECT * FROM decisions WHERE status='pending' ORDER BY priority DESC LIMIT 5", con)
    st.subheader("Top pending recommendations")
    if len(dec): st.dataframe(dec[["area","problem","action","priority"]], use_container_width=True)
    else: st.info("No pending recommendations — visit the Decision Intelligence Engine.")

elif page == "Business Growth":
    st.title("Business Growth Intelligence"); k = kpis(f); st.json({k2: round(float(v),2) for k2,v in k.items()})
    st.plotly_chart(px.bar(f.groupby("category").agg(revenue=("revenue","sum"),profit=("profit","sum")).reset_index(), x="category", y=["revenue","profit"], barmode="group"), use_container_width=True)
    st.plotly_chart(px.bar(f.groupby("region").revenue.sum().reset_index(), x="region", y="revenue", title="Revenue by region"), use_container_width=True)
    st.subheader("Drill-down (filtered records)"); st.dataframe(f.head(500), use_container_width=True)
    st.download_button("Download filtered CSV", f.to_csv(index=False), "cortexora_filtered.csv")

elif page == "Demand Forecasting":
    st.title("Demand Forecasting & Inventory")
    cat = st.selectbox("Category", sorted(products.category.unique())); s = weekly_series(df, cat, products)
    ev = evaluate(s); st.write(f"Chronological split — train ends {ev['train_end']}. Test totals: {ev['test_actual_total']:.0f} units")
    st.dataframe(pd.DataFrame({m: ev[m] for m in ["moving_average_4w","seasonal_naive"]}).T)
    fc = forecast_next(s); hist = s.reset_index(); hist.columns = ["week","forecast"]
    st.plotly_chart(px.line(pd.concat([hist.tail(26), fc]), x="week", y="forecast", title=f"{cat} weekly demand: history + forecast (80% interval in table)"), use_container_width=True)
    st.dataframe(fc, use_container_width=True)
    st.subheader("Inventory reorder plan (forecast-based, 95% service-level assumption)")
    stats = daily_demand_stats(df)
    stock = inv.merge(products[["product_id","category","unit_cost","list_price"]], on="product_id").merge(stats, on="product_id", how="left").fillna(0)
    plan = reorder_plan(stock)
    st.dataframe(plan[["product_id","category","stock_on_hand","forecast_daily","lead_time_days","safety_stock","recommended_reorder_qty","estimated_order_cost","stockout_risk"]], use_container_width=True)
    st.download_button("Download reorder plan CSV", plan.to_csv(index=False), "reorder_plan.csv")

elif page == "Pricing Simulator":
    st.title("Pricing & Profit — assumption-based simulator")
    st.info("Elasticity below is YOUR assumption, not an estimated causal effect. Results are scenarios, not predictions.")
    p = st.selectbox("Product", products.product_name); row = products[products.product_name==p].iloc[0]
    chg = st.slider("Price change %", -30, 30, 10); elas = st.slider("Assumed elasticity", -3.0, -0.1, -1.2)
    sold = items[items.product_id==row.product_id]; base_q, base_rev = sold.qty.sum(), (sold.qty*sold.unit_price*(1-sold.discount)).sum()
    new_q = base_q*(1+elas*chg/100); new_rev = new_q*row.list_price*(1+chg/100)
    st.metric("Scenario revenue", f"${new_rev:,.0f}", f"{new_rev/base_rev-1:+.1%} vs observed ${base_rev:,.0f} (observed 24-mo total)")
    st.subheader("Discount effectiveness (observed association — NOT a causal effect)")
    st.dataframe(discount_effectiveness(f), use_container_width=True)
    st.subheader("Break-even analysis")
    fixed = st.number_input("Monthly fixed cost to cover ($)", value=10000.0, step=1000.0)
    be = breakeven_units(fixed, row.list_price, row.unit_cost)
    st.write(f"{p}: contribution/unit = ${row.list_price-row.unit_cost:,.2f} → break-even = {'never (contribution ≤ 0)' if be==float('inf') else f'{be:,.0f} units'}")

elif page == "Customer Intelligence":
    st.title("Customer Intelligence (RFM + Churn Model)")
    r = rfm(orders, items); st.plotly_chart(px.histogram(r, x="segment", color="segment"), use_container_width=True)
    st.dataframe(r.sort_values("monetary", ascending=False).head(100), use_container_width=True)
    st.subheader("Churn prediction — validated model (Phase 4)")
    st.caption("Label: no purchase in the 90 days after cutoff (proxy — retail has no cancellation event). "
               "Trained on synthetic demo data: metrics validate the pipeline, not real-world performance. See docs/06_MODEL_CARD_CHURN.md.")
    from cortexora.models.churn import build_dataset, train_and_evaluate, predict_risk
    @st.cache_resource
    def _train():
        cutoff = pd.to_datetime(orders.order_date).max() - pd.Timedelta(days=90)
        data = build_dataset(orders, items, cutoff)
        return train_and_evaluate(data), data
    try:
        result, data = _train(); rep = result["report"]
        st.write(f"Best model: **{rep['best_model']}** · {rep['n_customers']} customers · observed churn rate {rep['churn_rate']:.1%} · hold-out n={rep['test_size']}")
        st.dataframe(pd.DataFrame(rep["results"]).T, use_container_width=True)
        st.bar_chart(pd.Series(rep["feature_importance"], name="importance (model explanation, not causal)"))
        risk = predict_risk(result["model"], data)
        st.subheader("Highest-risk customers"); st.dataframe(risk.head(50), use_container_width=True)
        st.download_button("Download risk list CSV", risk.to_csv(index=False), "churn_risk.csv")
    except ValueError as e:
        st.error(str(e))

elif page == "Marketing Performance":
    st.title("Marketing Performance"); st.caption("CAC is a spend/conversions proxy. ROAS is not shown: no attribution join exists in this data — attributed ≠ incremental.")
    st.dataframe(marketing_metrics(mkt), use_container_width=True)
    st.plotly_chart(px.bar(mkt.groupby("channel").spend.sum().reset_index(), x="channel", y="spend"), use_container_width=True)
    st.subheader("Budget allocation optimizer (fitted response curves, scenarios — not causal incrementality)")
    budget = st.slider("Total weekly budget ($)", 500, 10000, 3300)
    opt = optimize_budget(mkt, total_budget=float(budget))
    st.dataframe(opt["curves"], use_container_width=True); st.caption(opt.get("note",""))
    if "expected_gain_pct" in opt:
        st.metric("Expected conversions change vs current shares (same budget)", f"{opt['expected_gain_pct']:+.1f}%")
        comp = pd.DataFrame({"channel": list(opt["allocation"]), "current": [opt["current_allocation"][c] for c in opt["allocation"]], "optimized": list(opt["allocation"].values())})
        st.plotly_chart(px.bar(comp, x="channel", y=["current","optimized"], barmode="group"), use_container_width=True)

elif page == "Decision Intelligence Engine":
    st.title("Decision Intelligence Engine")
    st.caption("Priority = √expected_impact × confidence × urgency. Human approval required — no autonomous actions.")
    stats = daily_demand_stats(df)
    stock = inv.merge(products[["product_id","category","unit_cost","list_price"]], on="product_id").merge(stats, on="product_id", how="left").fillna(0)
    plan = reorder_plan(stock)
    recs = (inventory_recommendations(plan) + budget_recommendation(optimize_budget(mkt))
            + discount_recommendation(discount_effectiveness(df)) + churn_recommendations(rfm(orders, items)))
    if st.button("Generate recommendations from current data"): persist(recs, DB_PATH); st.success(f"{len(recs)} generated (duplicates ignored)")
    with sqlite3.connect(DB_PATH) as con: dec = pd.read_sql("SELECT * FROM decisions ORDER BY priority DESC", con)
    for r in dec.itertuples():
        st.write(f"**{r.recommendation_id} · {r.area}** — {r.problem} → {r.action}  \nEvidence: {r.evidence} · Priority {r.priority} · Status **{r.status}**")
        b = st.columns(3)
        if b[0].button("Approve", key=r.recommendation_id+"a"): set_status(r.recommendation_id,"approved",DB_PATH); st.rerun()
        if b[1].button("Reject", key=r.recommendation_id+"r"): set_status(r.recommendation_id,"rejected",DB_PATH); st.rerun()
        if b[2].button("Defer", key=r.recommendation_id+"d"): set_status(r.recommendation_id,"deferred",DB_PATH); st.rerun()

elif page == "Data Quality & Monitoring":
    st.title("Data Quality & Model Monitoring")
    from cortexora.monitoring.quality import run_all
    frames = {t: load_table(t) for t in ["orders","order_items","customers","products"]}
    st.dataframe(run_all(frames), use_container_width=True)
    st.info("Forecast monitoring: re-run Demand Forecasting after new data lands and compare WAPE vs the seasonal-naive baseline. Drift ≠ degradation — see docs/03.")

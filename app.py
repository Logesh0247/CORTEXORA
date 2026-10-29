"""CORTEXORA — The Intelligence Engine for Predictive Business Decisions.
Run: streamlit run app.py  (run scripts/run_etl.py first)"""
import sqlite3
import pandas as pd, plotly.express as px, streamlit as st
from cortexora.config import DB_PATH
from cortexora.pipelines.etl import load_table
from cortexora.analytics.metrics import enrich, kpis, period_compare, marketing_metrics
from cortexora.models.forecasting import weekly_series, evaluate, forecast_next, rfm
from cortexora.decision_engine.engine import stockout_recommendations, churn_recommendations, inventory_recommendations, budget_recommendation, discount_recommendation, persist, set_status, record_outcome, load_decisions, outcome_summary
from cortexora.optimization.optimize import reorder_plan, daily_demand_stats, discount_effectiveness, breakeven_units, optimize_budget
from cortexora.analytics.experiments import ab_conversion, required_sample_size, srm_check, diff_in_diff, mmm_readiness
from cortexora.analytics.competitor import validate_snapshots, price_gaps
from cortexora.reports.report import generate_markdown_report
import numpy as np

st.set_page_config(page_title="CORTEXORA — Intelligence Engine", page_icon="🧠", layout="wide", initial_sidebar_state="expanded")
px.defaults.template = "plotly_dark"
px.defaults.color_discrete_sequence = ["#38bdf8", "#818cf8", "#34d399", "#fbbf24", "#fb7185", "#22d3ee"]
if not DB_PATH.exists():
    with st.spinner("First run: building the CORTEXORA warehouse from sample data (seed=42)…"):
        from cortexora.config import SAMPLE_DIR
        from cortexora.data.generate_sample import generate
        from cortexora.pipelines.etl import run as _etl_run
        if not (SAMPLE_DIR / "orders.csv").exists(): generate(SAMPLE_DIR)
        _etl_run(SAMPLE_DIR, DB_PATH)
orders, items, products, inv, mkt = (load_table(t) for t in ["orders","order_items","products","inventory_snapshots","marketing_spend"])
df = enrich(orders, items).merge(products[["product_id","category"]], on="product_id")

# ================= Interactive navigation (grouped, searchable, stateful) =================
NAV = [
    ("OVERVIEW", [("🏠", "Home / Executive Overview")]),
    ("ANALYZE — what happened & why", [("📈", "Business Growth"), ("🎯", "Marketing Performance"), ("🥊", "Competitor Intelligence")]),
    ("PREDICT & OPTIMIZE — what next", [("🔮", "Demand Forecasting"), ("👥", "Customer Intelligence"), ("💲", "Pricing & Profit Optimization")]),
    ("DECIDE — what should we do", [("🧠", "Decision Intelligence Engine"), ("🧪", "Experiments & Causal Lab")]),
    ("SYSTEM", [("🩺", "Data Quality & Monitoring"), ("📄", "Reports"), ("⚙️", "Settings & About")]),
]
ALL_PAGES = [pg for _, items_ in NAV for _, pg in items_]
PAGE_ICON = {pg: ic for _, items_ in NAV for ic, pg in items_}
PAGE_SECTION = {pg: sec for sec, items_ in NAV for _, pg in items_}

def go(target: str):
    """Navigate to another module (used by sidebar, KPI cards and shortcuts)."""
    st.session_state["page"] = target
    st.session_state["jump_box"] = target  # keep the Jump-to box in sync, or it would override us

def _jump():
    st.session_state["page"] = st.session_state["jump_box"]

def _reset_filters():
    import datetime as _dt
    st.session_state["filter_cats"] = sorted(df.category.unique())
    st.session_state["filter_regions"] = sorted(df.region.unique())
    st.session_state["filter_dates"] = [df.order_date.min().date(), df.order_date.max().date()]

if "page" not in st.session_state or st.session_state["page"] not in ALL_PAGES:
    st.session_state["page"] = "Home / Executive Overview"

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif}
.stApp{background:radial-gradient(1200px 500px at 85% -5%,rgba(56,189,248,.16),transparent 60%),radial-gradient(900px 450px at 8% 0%,rgba(129,140,248,.13),transparent 55%),#070d18;color:#e8eef6}
.block-container{padding-top:.8rem;padding-bottom:2rem;max-width:1500px}
h1{font-weight:850!important;letter-spacing:-.03em;background:linear-gradient(90deg,#fff,#7dd3fc 55%,#a5b4fc);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:.1rem}
h2,h3{font-weight:750!important;letter-spacing:-.015em;color:#f1f6fd}
p,li,label{color:#c6d3e6}
section[data-testid="stSidebar"]{background:linear-gradient(180deg,#0a1526,#081020 70%);border-right:1px solid #1d3153}
section[data-testid="stSidebar"] .stButton button{justify-content:flex-start;text-align:left;border-radius:10px;border:1px solid transparent;padding:.42rem .65rem;font-weight:600;transition:all .15s ease}
section[data-testid="stSidebar"] .stButton button:hover{border-color:#35619b;transform:translateX(2px)}
section[data-testid="stSidebar"] button[kind="primary"]{background:linear-gradient(90deg,#0284c7,#4f46e5);border:none;box-shadow:0 4px 18px rgba(56,189,248,.35)}
.stButton button{border-radius:10px;font-weight:650;border:1px solid #2b4a73;transition:all .15s ease}
.stButton button:hover{border-color:#38bdf8;box-shadow:0 4px 16px rgba(56,189,248,.22);transform:translateY(-1px)}
button[kind="primary"]{background:linear-gradient(90deg,#0284c7,#4f46e5)!important;border:none!important}
div[data-testid="stMetric"]{background:linear-gradient(160deg,#101f36,#0b1626);border:1px solid #223d64;border-radius:12px;padding:10px 14px}
div[data-testid="stMetric"] label{color:#8fb0d8}
div[data-testid="stExpander"]{background:#0c1728;border:1px solid #1e3557;border-radius:12px}
div[data-testid="stDataFrame"]{border:1px solid #1e3557;border-radius:12px;overflow:hidden}
div[data-baseweb="select"]>div,div[data-baseweb="input"]>div{background:#0d1a2e;border-color:#27466e;border-radius:9px}
.stTabs [data-baseweb="tab-list"]{gap:6px;background:#0b1728;border:1px solid #1e3557;border-radius:12px;padding:5px}
.stTabs [data-baseweb="tab"]{border-radius:8px;padding:7px 16px;font-weight:650;color:#a9c0dc}
.stTabs [aria-selected="true"]{background:linear-gradient(90deg,#0284c7,#4f46e5);color:#fff!important}
hr{border-color:#1c3355}
::-webkit-scrollbar{width:9px;height:9px}::-webkit-scrollbar-thumb{background:#25456e;border-radius:99px}
.cx-hero{background:linear-gradient(110deg,#0b2447 0%,#123a6e 45%,#2b2a72 100%);border:1px solid #2f5b8f;border-radius:16px;padding:20px 24px;margin:4px 0 14px 0;box-shadow:0 12px 34px rgba(2,10,28,.5)}
.cx-hero .brand{font-size:1.65rem;font-weight:900;letter-spacing:-.02em;color:#fff}
.cx-hero .tag{color:#bcd7f7;font-size:.92rem;margin-top:2px}
.cx-pill{display:inline-block;background:rgba(125,211,252,.14);border:1px solid rgba(125,211,252,.45);color:#d8efff;border-radius:999px;padding:3px 11px;font-size:.75rem;margin:8px 6px 0 0;font-weight:600}
.cx-kpi{background:linear-gradient(160deg,#122540,#0b1729);border:1px solid #264873;border-radius:14px;padding:16px 16px 13px;min-height:118px;box-shadow:0 8px 22px rgba(0,0,0,.25);transition:all .15s ease}
.cx-kpi:hover{border-color:#38bdf8;transform:translateY(-2px)}
.cx-kpi .label{font-size:.72rem;color:#8fb0d8;text-transform:uppercase;letter-spacing:.09em;font-weight:700}
.cx-kpi .value{font-size:1.55rem;font-weight:850;color:#fff;margin:3px 0 1px}
.cx-kpi .sub{font-size:.78rem;color:#9db4d4}
.cx-kpi .up{color:#34d399;font-weight:700}.cx-kpi .down{color:#fb7185;font-weight:700}
.cx-card{background:linear-gradient(165deg,#101f36,#0a1524);border:1px solid #223d64;border-radius:14px;padding:16px 18px;min-height:120px}
.cx-card h4{margin:0 0 6px 0;color:#fff}.cx-card p{color:#a9c0dc;font-size:.88rem;margin:0}
.cx-navsec{font-size:.7rem;color:#7f97b5;letter-spacing:.1em;font-weight:800;margin:15px 0 3px 0}
.cx-brand{background:linear-gradient(120deg,#0e2c52,#232064);border:1px solid #2f5b8f;border-radius:14px;padding:14px 16px;margin-bottom:6px}
.cx-brand .b{font-size:1.25rem;font-weight:900;color:#fff;letter-spacing:.02em}
.cx-brand .s{font-size:.74rem;color:#a9cdf5;line-height:1.35}
</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("""<div class="cx-brand"><div class="b">🧠 CORTEXORA</div>
    <div class="s">The Intelligence Engine for Predictive Business Decisions<br><i>Predict the Future. Optimize the Present. Engineer Business Growth.</i></div></div>""", unsafe_allow_html=True)
    st.selectbox("🔎 Jump to… (type to search)", ALL_PAGES,
                 index=ALL_PAGES.index(st.session_state["page"]), key="jump_box", on_change=_jump)
    for section, items_ in NAV:
        st.markdown(f"<div class='cx-navsec'>{section}</div>", unsafe_allow_html=True)
        for icon, name in items_:
            active = st.session_state["page"] == name
            st.button(f"{icon}  {name}", key=f"nav_{name}", use_container_width=True,
                      type="primary" if active else "secondary", on_click=go, args=(name,))
    st.divider()
    try:
        _pend = int((load_decisions(DB_PATH).status == "pending").sum())
    except Exception: _pend = 0
    st.metric("Pending decisions", _pend)
    st.caption(f"Data through {df.order_date.max().date()} · {len(df):,} line items")
    st.warning("⚠️ Synthetic demo data (seed=42) — not real business results.")
    with st.expander("🎛️ Global filters (apply to every page)", expanded=True):
        cats = st.multiselect("Category", sorted(df.category.unique()), default=sorted(df.category.unique()), key="filter_cats")
        dmin, dmax = st.date_input("Date range", [df.order_date.min().date(), df.order_date.max().date()], key="filter_dates")
        regions = st.multiselect("Region", sorted(df.region.unique()), default=sorted(df.region.unique()), key="filter_regions")
        st.button("↺ Reset all filters", on_click=_reset_filters, use_container_width=True)

page = st.session_state["page"]
_q = st.columns([1,1,1,1,3])
_q[0].button("🏠 Overview", key="top_home", use_container_width=True, on_click=go, args=("Home / Executive Overview",))
_q[1].button("🔮 Forecast", key="top_fc", use_container_width=True, on_click=go, args=("Demand Forecasting",))
_q[2].button("🧠 Decisions", key="top_dec", use_container_width=True, type="primary", on_click=go, args=("Decision Intelligence Engine",))
_q[3].button("📄 Reports", key="top_rep", use_container_width=True, on_click=go, args=("Reports",))
_q[4].caption("Quick nav — or use the grouped sidebar / Jump-to search. Filters on the left apply everywhere.")
f = df[df.category.isin(cats) & df.region.isin(regions) & df.order_date.between(pd.Timestamp(dmin), pd.Timestamp(dmax))]
if f.empty: st.warning("No records match the current filters — widen the category/region/date selection in the sidebar.")
_pend_n = 0
try: _pend_n = int((load_decisions(DB_PATH).status == "pending").sum())
except Exception: pass
st.markdown(f"""<div class="cx-hero"><div class="brand">{PAGE_ICON.get(page,'')} {page}</div>
<div class="tag">{PAGE_SECTION.get(page,'')} · CORTEXORA Intelligence Engine</div>
<span class="cx-pill">📅 Data through {df.order_date.max().date()}</span>
<span class="cx-pill">🧠 {_pend_n} pending decisions</span>
<span class="cx-pill">🗂️ {len(f):,} records in scope</span>
<span class="cx-pill">⚠️ Synthetic demo data</span></div>""", unsafe_allow_html=True)

if page == "Home / Executive Overview":
    st.title("Executive Overview")
    st.caption("Every number below is computed live from the warehouse for the current filters. Use the tabs to explore, then jump into the module behind any number.")
    k = kpis(f); pc0 = period_compare(f).set_index("metric")
    def _delta(metric):
        v = pc0.loc[metric, "change_pct"]; cls = "up" if v >= 0 else "down"; arrow = "▲" if v >= 0 else "▼"
        return f"<span class='{cls}'>{arrow} {abs(v):.1f}%</span> vs prior 30d"
    cards = [("Revenue", f"${k['revenue']:,.0f}", _delta("revenue")), ("Profit", f"${k['profit']:,.0f}", _delta("profit")),
             ("Margin", f"{k['margin']:.1%}", "profit / revenue"), ("Orders", f"{k['orders']:,}", _delta("orders")),
             ("Avg order value", f"${k['aov']:,.2f}", _delta("aov"))]
    c = st.columns(5)
    for col, (label, val, sub) in zip(c, cards):
        col.markdown(f"<div class='cx-kpi'><div class='label'>{label}</div><div class='value'>{val}</div><div class='sub'>{sub}</div></div>", unsafe_allow_html=True)
    s = st.columns(4)
    s[0].button("📈 Why did this move? → Growth", use_container_width=True, on_click=go, args=("Business Growth",))
    s[1].button("🔮 What happens next? → Forecast", use_container_width=True, on_click=go, args=("Demand Forecasting",))
    s[2].button("🧠 What should we do? → Decisions", use_container_width=True, type="primary", on_click=go, args=("Decision Intelligence Engine",))
    s[3].button("🩺 Can we trust this? → Monitoring", use_container_width=True, on_click=go, args=("Data Quality & Monitoring",))
    # Insight cards computed from the filtered data
    if len(f):
        by_cat = f.groupby("category").revenue.sum(); top_cat = by_cat.idxmax()
        by_reg = f.groupby("region").revenue.sum(); top_reg = by_reg.idxmax()
        low_margin = f.groupby("category").apply(lambda g: g.profit.sum()/g.revenue.sum() if g.revenue.sum() else 0).idxmin()
        ic = st.columns(3)
        ic[0].markdown(f"<div class='cx-card'><h4>🏆 Top category</h4><p><b style='color:#fff'>{top_cat}</b> drives ${by_cat.max():,.0f} ({by_cat.max()/by_cat.sum():.0%} of in-scope revenue).</p></div>", unsafe_allow_html=True)
        ic[1].markdown(f"<div class='cx-card'><h4>🗺️ Strongest region</h4><p><b style='color:#fff'>{top_reg}</b> leads with ${by_reg.max():,.0f} in revenue.</p></div>", unsafe_allow_html=True)
        ic[2].markdown(f"<div class='cx-card'><h4>⚠️ Margin watch</h4><p><b style='color:#fff'>{low_margin}</b> has the thinnest margin in scope — see Pricing & Profit Optimization before discounting further.</p></div>", unsafe_allow_html=True)
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Performance trend", "🧩 Segments", "🔁 Period comparison", "🧠 Needs your decision"])
    with tab1:
        trend = f.groupby("order_date").agg(revenue=("revenue","sum"), profit=("profit","sum")).reset_index()
        fig = px.area(trend, x="order_date", y="revenue", title="Revenue trend (actuals)")
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10,r=10,t=40,b=10))
        st.plotly_chart(fig, use_container_width=True)
        st.plotly_chart(px.line(trend, x="order_date", y="profit", title="Profit trend (actuals)"), use_container_width=True)
    with tab2:
        a, b = st.columns(2)
        a.plotly_chart(px.bar(f.groupby("category").agg(revenue=("revenue","sum"),profit=("profit","sum")).reset_index(), x="category", y=["revenue","profit"], barmode="group", title="Category"), use_container_width=True)
        b.plotly_chart(px.pie(f.groupby("region").revenue.sum().reset_index(), names="region", values="revenue", hole=.45, title="Revenue share by region"), use_container_width=True)
    with tab3:
        st.dataframe(period_compare(f), use_container_width=True)
        st.caption("Current 30 days vs the preceding 30 days, using the shared metric definitions (docs/03).")
    with tab4:
        with sqlite3.connect(DB_PATH) as con: dec = pd.read_sql("SELECT * FROM decisions WHERE status='pending' ORDER BY priority DESC LIMIT 5", con)
        if len(dec):
            st.dataframe(dec[["area","problem","action","priority"]], use_container_width=True)
            st.button("Review & decide → Decision Engine", type="primary", on_click=go, args=("Decision Intelligence Engine",))
        else: st.info("No pending recommendations — generate them in the Decision Intelligence Engine.")

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

elif page == "Pricing & Profit Optimization":
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
    st.subheader("Marketing Mix Modelling — readiness gate")
    gate = mmm_readiness(mkt, has_revenue_outcome=False); st.dataframe(gate, use_container_width=True)
    if gate.Met.all(): st.success("All checks pass — MMM fitting is enabled.")
    else: st.warning("MMM is NOT fitted: the checks above fail. An unidentifiable model shown confidently is worse than no model. Needed: a revenue outcome joinable to weekly channel spend, plus external controls (price/promo/seasonality). The budget optimizer above is a simpler, honestly-labelled alternative on this data.")

elif page == "Experiments & Causal Lab":
    st.title("Causal Inference & Experimentation Lab")
    st.caption("Causal claims require a causal design. Randomised A/B test → effect + uncertainty. No randomisation → no causal claim from this page.")
    st.subheader("A/B test analyser (conversion)")
    c1, c2 = st.columns(2)
    with c1: n_t = st.number_input("Treatment visitors", 1, value=1200); cv_t = st.number_input("Treatment conversions", 0, value=156)
    with c2: n_c = st.number_input("Control visitors", 1, value=1200); cv_c = st.number_input("Control conversions", 0, value=132)
    try:
        r = ab_conversion(int(n_t), int(cv_t), int(n_c), int(cv_c)); s = srm_check(int(n_t), int(n_c))
        m = st.columns(4); m[0].metric("Control rate", f"{r['rate_ctrl']:.2%}"); m[1].metric("Treatment rate", f"{r['rate_treat']:.2%}")
        m[2].metric("Absolute effect", f"{r['abs_effect']:+.2%}", f"{r['rel_effect_pct']:+.1f}% relative"); m[3].metric("p-value", f"{r['p_value']:.4f}")
        st.write(f"95% CI for the effect: [{r['ci_low']:+.2%}, {r['ci_high']:+.2%}] · Cohen's h = {r['cohens_h']:.3f} · "
                 + ("**Statistically significant** at 5% — still check practical significance and novelty effects before shipping." if r["significant"] else "**Not significant** — the data do not rule out zero effect; do not ship on this evidence."))
        if s["srm_suspected"]: st.error(f"⚠️ SRM suspected (split {s['observed_share']:.1%} vs intended {s['expected_share']:.0%}, p={s['p_value']:.4f}): randomisation may be broken — investigate before trusting any result.")
    except ValueError as e: st.error(str(e))
    st.subheader("Design guidance — required sample size")
    base = st.slider("Baseline conversion rate", 0.01, 0.50, 0.11); mde = st.slider("Minimum detectable effect (absolute)", 0.005, 0.05, 0.02, step=0.005)
    st.write(f"You need ≈ **{required_sample_size(base, mde):,} visitors per group** (α=0.05, power=0.80). Fix this *before* launching; peeking and stopping early inflates false positives.")
    st.subheader("Difference-in-differences (quasi-experiment) — synthetic demo")
    st.caption("Demo data with a known +8 effect, generated in-page and labelled as such. DiD is causal ONLY under parallel trends.")
    rng = np.random.default_rng(0); rows = []
    for unit in range(60):
        tr = int(unit < 30); b = rng.normal(100, 5)
        for post_ in (0,1): rows.append(dict(y=b + 10*post_ + (8 if tr and post_ else 0) + rng.normal(0,2), treated=tr, post=post_))
    d = diff_in_diff(pd.DataFrame(rows))
    st.write(f"DiD estimate: **{d['did_effect']:+.2f}** (95% CI [{d['ci_low']:.2f}, {d['ci_high']:.2f}], p={d['p_value']:.4f}) · pre-period level gap = {d['pre_period_gap']:.2f} (a large gap warns parallel trends may fail)")

elif page == "Competitor Intelligence":
    st.title("Competitor & Market Intelligence Radar")
    st.warning("No live competitor feed is connected. This page analyses snapshots YOU supply (compliantly collected public prices with source + timestamp) — it does not scrape or simulate a live feed.")
    template = pd.DataFrame(dict(product_id=[1,2], competitor=["RivalCo","RivalCo"], competitor_price=[99.0,49.0],
                                 observed_at=["2026-10-01","2026-10-01"], source_url=["https://example.com/p1","https://example.com/p2"]))
    st.download_button("Download snapshot template CSV", template.to_csv(index=False), "competitor_template.csv")
    src = st.radio("Snapshot source", ["Load clearly-labelled example", "Upload my CSV"])
    snap = None
    if src.startswith("Load"):
        snap = template.copy(); snap["competitor_price"] = [products.list_price.iloc[0]*0.85, products.list_price.iloc[1]*1.05]; st.info("Example snapshot (illustrative values derived from our own list prices) — not real competitor data.")
    else:
        up = st.file_uploader("Competitor snapshot CSV", type="csv")
        if up is not None:
            try: snap = pd.read_csv(up)
            except Exception as e: st.error(f"Could not read CSV: {e}")
    if snap is not None:
        try:
            gaps = price_gaps(validate_snapshots(snap, products.product_id), products)
            st.dataframe(gaps, use_container_width=True)
            alerts = gaps[gaps.alert]
            st.metric("Undercut alerts (competitor ≥5% cheaper)", len(alerts))
            for a in alerts.itertuples(): st.error(f"⚠️ {a.competitor} undercuts {a.product_name} by {abs(a.gap_pct):.1f}% (theirs ${a.competitor_price:.2f} vs ours ${a.list_price:.2f}, observed {a.observed_at}, source: {a.source_url})")
            st.download_button("Download comparison report CSV", gaps.to_csv(index=False), "competitor_report.csv")
        except ValueError as e: st.error(f"Invalid snapshot: {e}")

elif page == "Decision Intelligence Engine":
    st.title("Decision Intelligence Engine")
    st.caption("Priority = √expected_impact × confidence × urgency. Human approval required — no autonomous actions. "
               "Workflow: pending → approved/rejected/deferred → (after the measurement period) measured, with expected-vs-actual compared below.")
    stats = daily_demand_stats(df)
    stock = inv.merge(products[["product_id","category","unit_cost","list_price"]], on="product_id").merge(stats, on="product_id", how="left").fillna(0)
    plan = reorder_plan(stock)
    recs = (inventory_recommendations(plan) + budget_recommendation(optimize_budget(mkt))
            + discount_recommendation(discount_effectiveness(df)) + churn_recommendations(rfm(orders, items)))
    if st.button("Generate recommendations from current data"): persist(recs, DB_PATH); st.success(f"{len(recs)} generated (duplicates ignored)")
    dec = load_decisions(DB_PATH)
    counts = dec.status.value_counts().to_dict() if len(dec) else {}
    st.write("**Decision pipeline:** " + (" · ".join(f"{k}: {v}" for k, v in counts.items()) if counts else "no decisions yet"))
    owner = st.text_input("Decision owner (recorded on approve/record)", value="")
    for r in dec.itertuples():
        due = ""
        if pd.notna(r.decided_at) and pd.notna(r.measurement_period_days):
            due = f" · outcome due {(pd.Timestamp(r.decided_at) + pd.Timedelta(days=int(r.measurement_period_days))).date()}"
        st.write(f"**{r.recommendation_id} · {r.area}** — {r.problem} → {r.action}  \nEvidence: {r.evidence} · Expected impact ${r.expected_impact:,.0f} · Priority {r.priority} · Status **{r.status}**{due}")
        if r.area == "Pricing" and r.status == "pending":
            st.caption("↳ Before acting, design this as a test in **Experiments & Causal Lab** (sidebar) so the outcome is causal, not anecdotal.")
        b = st.columns(3)
        if b[0].button("Approve", key=r.recommendation_id+"a"): set_status(r.recommendation_id,"approved",DB_PATH,owner); st.rerun()
        if b[1].button("Reject", key=r.recommendation_id+"r"): set_status(r.recommendation_id,"rejected",DB_PATH,owner); st.rerun()
        if b[2].button("Defer", key=r.recommendation_id+"d"): set_status(r.recommendation_id,"deferred",DB_PATH,owner); st.rerun()
        if r.status == "approved":
            with st.expander(f"Record actual outcome — {r.recommendation_id}"):
                actual = st.number_input("Actual outcome (same units as expected impact, $)", key=r.recommendation_id+"act", value=float(r.expected_impact))
                note = st.text_input("How was it measured? (source, period, caveats)", key=r.recommendation_id+"note")
                if st.button("Record outcome", key=r.recommendation_id+"rec"):
                    if not note: st.error("A measurement note is required — an outcome without a source is not evidence.")
                    else:
                        try: record_outcome(r.recommendation_id, actual, note, DB_PATH, owner); st.rerun()
                        except ValueError as e: st.error(str(e))
        if r.status == "measured":
            var = (r.actual_outcome - r.expected_impact) / abs(r.expected_impact) * 100 if r.expected_impact else 0
            st.caption(f"Measured: actual ${r.actual_outcome:,.0f} vs expected ${r.expected_impact:,.0f} ({var:+.1f}%) — {r.outcome_note}")
    st.subheader("Outcome tracking — did our decisions work?")
    s = outcome_summary(dec)
    if s["measured"] == 0:
        st.info("No measured outcomes yet. Approve a recommendation, act on it, wait its measurement period, then record the actual outcome above. CORTEXORA never invents outcome data.")
    else:
        m = st.columns(3); m[0].metric("Measured decisions", s["measured"]); m[1].metric("Median |variance| vs expected", f"{s['median_abs_variance_pct']:.1f}%"); m[2].metric("Within ±20% of expected", f"{s['within_20pct']:.0%}")
        det = s["detail"]
        st.plotly_chart(px.bar(det, x="recommendation_id", y="variance_pct", color="area", title="Outcome variance vs expectation (%) — calibration of the engine's estimates"), use_container_width=True)
        st.dataframe(s["by_area"], use_container_width=True)
        st.dataframe(det[["recommendation_id","area","expected_impact","actual_outcome","variance_pct","owner","outcome_note"]], use_container_width=True)
        st.caption("Persistent large positive/negative bias by area means that detector's impact estimates are mis-calibrated — adjust its confidence/assumptions, don't just celebrate or panic over one result.")
    st.subheader("Decision history (audit log)")
    st.dataframe(dec, use_container_width=True)
    st.download_button("Download decision history CSV", dec.to_csv(index=False), "cortexora_decision_history.csv")

elif page == "Reports":
    st.title("Reports")
    st.caption("The report renders computed values from the same functions as the dashboards — no hand-typed figures. Scope follows the sidebar filters.")
    import json as _json, pathlib as _pl
    cat_sel = st.selectbox("Forecast category in report", sorted(products.category.unique()))
    art = _pl.Path("cortexora/models/artifacts/churn_evaluation.json")
    churn_rep = _json.loads(art.read_text()) if art.exists() else None
    md = generate_markdown_report(f, evaluate(weekly_series(f, cat_sel, products)), churn_rep, load_decisions(DB_PATH),
                                  generated_for=f"Categories: {', '.join(cats)} · {dmin} → {dmax} · forecast: {cat_sel}")
    st.markdown(md)
    st.download_button("Download executive report (Markdown)", md, "cortexora_executive_report.md")
    st.download_button("Download decisions CSV", load_decisions(DB_PATH).to_csv(index=False), "cortexora_decisions.csv")

elif page == "Settings & About":
    st.title("Settings & About")
    st.markdown("## 🧠 CORTEXORA\n**The Intelligence Engine for Predictive Business Decisions**  \n*Predict the Future. Optimize the Present. Engineer Business Growth.*")
    from cortexora import __version__
    from cortexora.config import ROOT
    st.write(f"Version **{__version__}** · Database: `{DB_PATH}` · Project root: `{ROOT}`")
    st.warning("Demo configuration: synthetic data (seed=42), SQLite warehouse. For production: point CORTEXORA_DB to a persistent path/Postgres, replace the sample generator with a licensed real dataset (docs/04), and retrain models before any business use.")
    st.subheader("Metric definitions (single source of truth — docs/03)")
    st.markdown("- **Revenue** = Σ qty × unit_price × (1−discount) · **Margin** = profit/revenue · **AOV** = revenue/orders\n"
                "- **CAC (proxy)** = spend/conversions (no attribution join, so ROAS is intentionally not shown)\n"
                "- **Churn label** = no purchase within 90 days after cutoff · **Forecast error** = MAE/RMSE/WAPE on a chronological hold-out vs seasonal-naive baseline")
    st.subheader("Data pipeline")
    try:
        runs = load_table("pipeline_runs").sort_values("run_id", ascending=False).head(5); st.dataframe(runs, use_container_width=True)
    except Exception: st.info("No pipeline runs logged yet.")
    if st.button("Reload warehouse from sample CSVs (idempotent; decisions & run log are preserved)"):
        from cortexora.pipelines.etl import run as _run
        with st.spinner("Running ETL…"): _run(); st.cache_resource.clear(); st.success("Warehouse reloaded."); st.rerun()
    st.subheader("What CORTEXORA deliberately does not do")
    st.markdown("- No autonomous business actions — every recommendation needs a human decision.\n"
                "- No causal claims from observational pages (pricing/discount/marketing pages say so inline).\n"
                "- MMM fitting stays disabled until a joinable revenue outcome exists (readiness gate, Marketing page).\n"
                "- No live competitor feed is simulated — Competitor Intelligence uses your validated snapshots only.")

elif page == "Data Quality & Monitoring":
    st.title("Data Quality & Model Monitoring")
    st.caption("Three different things, never conflated: data drift ≠ prediction drift ≠ measured performance degradation. Only the last — computed on later *labelled* data — is evidence about accuracy.")
    from cortexora.monitoring.quality import run_all
    from cortexora.monitoring.drift import drift_report, performance_comparison
    st.subheader("Pipeline runs (logged by the ETL)")
    try:
        runs = load_table("pipeline_runs").sort_values("run_id", ascending=False)
        st.dataframe(runs.head(10), use_container_width=True)
        last_ok = runs[runs.status=="success"].finished_at.max()
        st.write(f"Last successful run: **{last_ok}** · Data current to **{orders.order_date.max()}** (end of the synthetic dataset — 'freshness' here means pipeline recency, not real-world recency).")
    except Exception: st.info("No pipeline runs logged yet — run `python scripts/run_etl.py`.")
    st.subheader("Data quality checks")
    frames = {t: load_table(t) for t in ["orders","order_items","customers","products"]}
    q = run_all(frames); st.dataframe(q, use_container_width=True)
    if (q.status=="FAIL").any(): st.error("FAIL checks present — analytical outputs should not be trusted until resolved.")
    st.subheader("Data drift — first 18 months (reference) vs last 6 months (current)")
    mid, end = df.order_date.min() + pd.Timedelta(days=540), df.order_date.max()
    ref, cur = df[df.order_date <= mid], df[df.order_date > end - pd.Timedelta(days=180)]
    st.dataframe(drift_report(ref, cur, ["qty","unit_price","discount","revenue"]), use_container_width=True)
    st.caption("PSI <0.10 stable · 0.10–0.25 moderate shift · >0.25 significant shift. A shift is a prompt to investigate, not proof the model broke.")
    st.subheader("Churn model — temporal performance monitoring")
    st.caption("Train on an earlier cohort, score a later labelled cohort. This is the only honest way to detect degradation before it hurts.")
    from cortexora.models.churn import build_dataset, train_and_evaluate, evaluate_on, FEATURES as CHURN_FEATURES
    @st.cache_resource
    def _monitor():
        maxd = pd.to_datetime(orders.order_date).max()
        ref_data = build_dataset(orders, items, maxd - pd.Timedelta(days=270))
        cur_data = build_dataset(orders, items, maxd - pd.Timedelta(days=90))
        trained = train_and_evaluate(ref_data); model = trained["model"]
        return trained["report"], evaluate_on(model, cur_data), cur_data
    try:
        ref_rep, cur_metrics, cur_data = _monitor()
        ref_metrics = ref_rep["results"][ref_rep["best_model"]]
        comp = performance_comparison(ref_metrics, cur_metrics)
        c = st.columns(3); c[0].metric("Reference PR-AUC (hold-out)", f"{comp['reference']:.3f}"); c[1].metric("Later-period PR-AUC", f"{comp['current']:.3f}", f"{comp['delta']:+.3f}"); c[2].metric("Degraded?", "YES — investigate" if comp["degraded"] else "No")
        st.write(comp["note"])
        st.write(f"Later cohort: {len(cur_data)} customers · observed churn {cur_metrics['observed_churn_rate']:.1%} vs mean predicted {cur_metrics['mean_predicted_probability']:.1%} (calibration gap is itself a monitoring signal).")
        st.dataframe(pd.DataFrame({"reference_holdout": ref_metrics, "later_period": {k: cur_metrics[k] for k in ref_metrics}}), use_container_width=True)
        import json, pathlib
        art = pathlib.Path("cortexora/models/artifacts/churn_evaluation.json")
        if art.exists():
            meta = json.loads(art.read_text()); st.caption(f"Registered artifact: {meta.get('model_version','?')} · trained {meta.get('trained_at','?')} · data cutoff {meta.get('data_cutoff','?')} · {meta.get('training_data','')}")
    except ValueError as e: st.error(str(e))

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

PAGE_META = {
 "Home / Executive Overview": ("Command centre", "What is happening, what is next, and what needs your decision — in one view."),
 "Business Growth": ("What happened? Why?", "Revenue, profit and segment drivers using the shared metric definitions."),
 "Marketing Performance": ("What happened? Why?", "Channel efficiency today, and where the next dollar of budget works hardest."),
 "Competitor Intelligence": ("External signals", "Compliantly-supplied competitor snapshots vs our prices — never a fake live feed."),
 "Demand Forecasting": ("What might happen next?", "Demand outlook with measured accuracy, plus the inventory actions it implies."),
 "Customer Intelligence": ("What might happen next?", "Who your customers are, and who is quietly leaving."),
 "Pricing & Profit Optimization": ("What should we do?", "Price, discount and break-even scenarios — assumption-based, honestly labelled."),
 "Decision Intelligence Engine": ("What should we do?", "Evidence-ranked recommendations. You approve; the system tracks whether it worked."),
 "Experiments & Causal Lab": ("Did it work? What is causal?", "Design and analyse A/B tests and quasi-experiments with proper uncertainty."),
 "Data Quality & Monitoring": ("Can we trust this?", "Data quality, pipeline health, drift and measured model performance."),
 "Reports": ("Share it", "Executive reports rendered from the same computed values as these dashboards."),
 "Settings & About": ("System", "Configuration, metric definitions, pipeline control and project identity."),
}

def page_intro():
    q, desc = PAGE_META.get(page, ("", ""))
    st.title(f"{PAGE_ICON.get(page,'')}  {page}")
    st.markdown(f"<div class='cx-intro'><span class='cx-q'>{q}</span><span class='cx-desc'>{desc}</span></div>", unsafe_allow_html=True)

def kpi_cards(cards, cols=None):
    """cards: list of (label, value, sub_html). Renders the gradient KPI strip."""
    cols = cols or st.columns(len(cards))
    for col, (label, val, sub) in zip(cols, cards):
        col.markdown(f"<div class='cx-kpi'><div class='label'>{label}</div><div class='value'>{val}</div><div class='sub'>{sub}</div></div>", unsafe_allow_html=True)

def C(fig, height=None):
    """Consistent chart styling for every Plotly figure in the app."""
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      margin=dict(l=8, r=8, t=44, b=8), font=dict(color="#c6d3e6"),
                      legend=dict(orientation="h", y=1.08, x=0), height=height or 340)
    fig.update_xaxes(gridcolor="rgba(90,130,180,.14)"); fig.update_yaxes(gridcolor="rgba(90,130,180,.14)")
    return fig

def delta_html(v, suffix="vs prior 30d"):
    cls = "up" if v >= 0 else "down"; arrow = "▲" if v >= 0 else "▼"
    return f"<span class='{cls}'>{arrow} {abs(v):.1f}%</span> {suffix}"


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
.cx-intro{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:-4px 0 14px 0}
.cx-q{background:linear-gradient(90deg,#0284c7,#4f46e5);color:#fff;border-radius:999px;padding:4px 13px;font-size:.78rem;font-weight:750;white-space:nowrap}
.cx-desc{color:#a9c0dc;font-size:.94rem}
div[data-testid="stVerticalBlockBorderWrapper"]{background:linear-gradient(165deg,rgba(18,35,62,.72),rgba(9,20,36,.72));border-radius:14px!important}
.stDownloadButton button{border-radius:10px;font-weight:650}
div[data-testid="stAlert"]{border-radius:12px}
input[type=number],textarea{border-radius:9px!important}
.cx-rec{border-left:3px solid #38bdf8;padding:2px 0 2px 10px;margin-bottom:4px}
.cx-rec .meta{color:#8fb0d8;font-size:.8rem}
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
    page_intro()
    st.markdown("### 🎛️ Interactive Dashboard — change any control and **everything below recalculates instantly**")
    # ---------- Control deck ----------
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([2.2, 1.2, 1.2, 1.2])
        _dmin, _dmax = df.order_date.min().date(), df.order_date.max().date()
        date_range = c1.slider("📅 Date range", _dmin, _dmax, (_dmin, _dmax), key="dash_dates")
        metric_label = c2.selectbox("📐 Metric", ["Revenue", "Profit", "Units", "Orders"], key="dash_metric")
        gran = c3.selectbox("⏱️ Granularity", ["Weekly", "Daily", "Monthly"], key="dash_gran")
        chart_type = c4.selectbox("📊 Chart type", ["Area", "Line", "Bar"], key="dash_chart")
        c5, c6, c7, c8 = st.columns([1.4, 1.4, 1.4, 1])
        breakdown = c5.selectbox("🧩 Break trend down by", ["Total", "Category", "Region", "Channel"], key="dash_break")
        dash_cats = c6.multiselect("Category", sorted(df.category.unique()), default=cats, key="dash_cats")
        dash_chans = c7.multiselect("Channel", sorted(df.channel.unique()), default=sorted(df.channel.unique()), key="dash_chans")
        top_n = c8.slider("🏆 Leaderboard rows", 5, 20, 10, key="dash_topn")
    metric_col = {"Revenue": "revenue", "Profit": "profit", "Units": "qty", "Orders": "revenue"}[metric_label]
    d = df[df.category.isin(dash_cats) & df.region.isin(regions) & df.channel.isin(dash_chans)
           & df.order_date.between(pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1]))]
    if d.empty:
        st.warning("No data for this combination — widen the date range or re-select categories/channels above.")
    # ---------- KPI strip (recomputed from d, delta vs equal-length prior period) ----------
    k = kpis(d) if len(d) else dict(revenue=0, profit=0, margin=0, orders=0, aov=0, units=0, customers=0)
    span_days = max((pd.Timestamp(date_range[1]) - pd.Timestamp(date_range[0])).days, 1)
    prior = df[df.category.isin(dash_cats) & df.region.isin(regions) & df.channel.isin(dash_chans)
               & df.order_date.between(pd.Timestamp(date_range[0]) - pd.Timedelta(days=span_days), pd.Timestamp(date_range[0]) - pd.Timedelta(days=1))]
    kp = kpis(prior) if len(prior) else dict(revenue=0, profit=0, orders=0, aov=0)
    def _d(cur, prev): return delta_html((cur / prev - 1) * 100 if prev else 0, f"vs prior {span_days}d")
    kpi_cards([("Revenue", f"${k['revenue']:,.0f}", _d(k['revenue'], kp['revenue'])),
               ("Profit", f"${k['profit']:,.0f}", _d(k['profit'], kp['profit'])),
               ("Margin", f"{k['margin']:.1%}", "profit / revenue"),
               ("Orders", f"{k['orders']:,}", _d(k['orders'], kp['orders'])),
               ("Avg order value", f"${k['aov']:,.2f}", _d(k['aov'], kp['aov']))])
    # ---------- Interactive trend chart ----------
    freq = {"Daily": "D", "Weekly": "W", "Monthly": "ME"}[gran]
    if len(d):
        if metric_label == "Orders":
            trend = (d.set_index("order_date").groupby([pd.Grouper(freq=freq)] + ([d[breakdown.lower()].rename(breakdown)] if breakdown != "Total" else []))["order_id"].nunique().rename("value").reset_index())
        else:
            keys = [pd.Grouper(key="order_date", freq=freq)] + ([breakdown.lower()] if breakdown != "Total" else [])
            trend = d.groupby(keys)[metric_col].sum().rename("value").reset_index()
        plot_fn = {"Area": px.area, "Line": px.line, "Bar": px.bar}[chart_type]
        kwargs = dict(x="order_date", y="value", title=f"{metric_label} · {gran}" + (f" · by {breakdown}" if breakdown != "Total" else ""))
        if breakdown != "Total": kwargs["color"] = breakdown.lower()
        st.plotly_chart(C(plot_fn(trend, **kwargs), 380), use_container_width=True)
    # ---------- Clickable category chart -> filters everything beneath it ----------
    left, right = st.columns([1.25, 1])
    clicked_cat = None
    with left:
        st.markdown("#### 🖱️ Click a category bar — the leaderboard & records below will filter to it")
        if "cat_click_reset" not in st.session_state: st.session_state["cat_click_reset"] = 0
        if len(d):
            cat_df = d.groupby("category")[metric_col].sum().reset_index()
            sel = st.plotly_chart(C(px.bar(cat_df, x="category", y=metric_col, color="category", title=f"{metric_label} by category — click a bar")), use_container_width=True,
                                  on_select="rerun", key=f"cat_chart_{st.session_state['cat_click_reset']}")
            try:
                pts = sel.selection.points
                if pts: clicked_cat = pts[0]["x"]
            except Exception: pass
        if clicked_cat:
            st.success(f"Filtering below to: **{clicked_cat}**")
            if st.button("↺ Clear category selection", key="clear_cat"):
                st.session_state["cat_click_reset"] += 1; st.rerun()
    with right:
        st.markdown("#### 🗺️ Region mix (updates with every control)")
        if len(d):
            reg_df = d.groupby("region")[metric_col].sum().reset_index()
            st.plotly_chart(C(px.pie(reg_df, names="region", values=metric_col, hole=.5, title=f"{metric_label} share by region"), 380), use_container_width=True)
    dd = d[d.category == clicked_cat] if clicked_cat else d
    # ---------- Product leaderboard with row selection ----------
    st.markdown(f"#### 🏆 Product leaderboard{' — ' + clicked_cat if clicked_cat else ''} (select a row to inspect it)")
    if len(dd):
        prod = (dd.merge(products[["product_id", "product_name"]], on="product_id")
                  .groupby(["product_name", "category"])
                  .agg(revenue=("revenue", "sum"), profit=("profit", "sum"), units=("qty", "sum"), orders=("order_id", "nunique"), avg_discount=("discount", "mean"))
                  .assign(margin=lambda x: x.profit / x.revenue).sort_values("revenue", ascending=False).head(top_n).reset_index())
        ev = st.dataframe(prod, use_container_width=True, height=360, on_select="rerun", selection_mode="single-row", key="prod_table")
        sel_rows = []
        try: sel_rows = ev.selection.rows
        except Exception: pass
        if sel_rows:
            r0 = prod.iloc[sel_rows[0]]
            a, b, c_ = st.columns(3)
            a.markdown(f"<div class='cx-card'><h4>📦 {r0.product_name}</h4><p>{r0.category} · revenue <b style='color:#fff'>${r0.revenue:,.0f}</b> · margin {r0.margin:.1%}</p></div>", unsafe_allow_html=True)
            b.markdown(f"<div class='cx-card'><h4>🧾 Demand</h4><p>{int(r0.units):,} units across {int(r0.orders):,} orders · avg discount {r0.avg_discount:.1%}</p></div>", unsafe_allow_html=True)
            with c_:
                st.markdown("<div class='cx-card'><h4>➡️ Next step</h4><p>Test a price move for this product in the simulator.</p></div>", unsafe_allow_html=True)
                st.button("💲 Open in Pricing Simulator →", key="go_pricing_sel", use_container_width=True, on_click=go, args=("Pricing & Profit Optimization",))
        else:
            st.caption("Tip: click any row above to see that product's detail card here.")
        st.download_button("⬇ Download dashboard data (CSV, current filters + click selection)", dd.to_csv(index=False), "cortexora_dashboard_data.csv")
    # ---------- Live insight cards ----------
    if len(d):
        by_cat = d.groupby("category").revenue.sum(); by_reg = d.groupby("region").revenue.sum()
        low_margin = d.groupby("category").apply(lambda g: g.profit.sum() / g.revenue.sum() if g.revenue.sum() else 0).idxmin()
        ic = st.columns(3)
        ic[0].markdown(f"<div class='cx-card'><h4>🏆 Top category</h4><p><b style='color:#fff'>{by_cat.idxmax()}</b> · ${by_cat.max():,.0f} ({by_cat.max()/by_cat.sum():.0%} of scope)</p></div>", unsafe_allow_html=True)
        ic[1].markdown(f"<div class='cx-card'><h4>🗺️ Strongest region</h4><p><b style='color:#fff'>{by_reg.idxmax()}</b> · ${by_reg.max():,.0f}</p></div>", unsafe_allow_html=True)
        ic[2].markdown(f"<div class='cx-card'><h4>⚠️ Margin watch</h4><p><b style='color:#fff'>{low_margin}</b> is thinnest-margin in scope — check Pricing before discounting.</p></div>", unsafe_allow_html=True)
    q1, q2, q3, q4 = st.columns(4)
    q1.button("📈 Growth deep-dive →", use_container_width=True, on_click=go, args=("Business Growth",))
    q2.button("🔮 Forecast →", use_container_width=True, on_click=go, args=("Demand Forecasting",))
    q3.button("🧠 Decisions →", use_container_width=True, type="primary", on_click=go, args=("Decision Intelligence Engine",))
    q4.button("📄 Export report →", use_container_width=True, on_click=go, args=("Reports",))

elif page == "Business Growth":
    page_intro(); k = kpis(f); pcg = period_compare(f).set_index("metric")
    kpi_cards([("Revenue", f"${k['revenue']:,.0f}", delta_html(pcg.loc['revenue','change_pct'])),
               ("Profit", f"${k['profit']:,.0f}", delta_html(pcg.loc['profit','change_pct'])),
               ("Margin", f"{k['margin']:.1%}", "profit / revenue"),
               ("Orders", f"{k['orders']:,}", delta_html(pcg.loc['orders','change_pct'])),
               ("Customers", f"{k['customers']:,}", f"{k['units']:,} units sold")])
    gt1, gt2, gt3 = st.tabs(["📊 Category & region", "📈 Trend explorer", "🔍 Drill-down data"])
    with gt1:
        a, b = st.columns(2)
        a.plotly_chart(C(px.bar(f.groupby("category").agg(revenue=("revenue","sum"),profit=("profit","sum")).reset_index(), x="category", y=["revenue","profit"], barmode="group", title="Revenue vs profit by category")), use_container_width=True)
        b.plotly_chart(C(px.bar(f.groupby("region").agg(revenue=("revenue","sum"),margin=("profit", lambda s: 0)).reset_index().assign(margin=f.groupby("region").apply(lambda g: g.profit.sum()/g.revenue.sum()).values), x="region", y="revenue", color="margin", color_continuous_scale="RdYlGn", title="Revenue by region (colour = margin)")), use_container_width=True)
        st.dataframe(f.groupby(["category"]).agg(revenue=("revenue","sum"), profit=("profit","sum"), orders=("order_id","nunique"), units=("qty","sum")).assign(margin=lambda d: d.profit/d.revenue).sort_values("revenue", ascending=False), use_container_width=True)
    with gt2:
        metric = st.radio("Metric", ["revenue","profit","qty"], horizontal=True, format_func=lambda m: {"revenue":"Revenue","profit":"Profit","qty":"Units"}[m])
        trend = f.groupby(["order_date","category"])[metric].sum().reset_index()
        st.plotly_chart(C(px.area(trend, x="order_date", y=metric, color="category", title=f"{metric.capitalize()} over time by category")), use_container_width=True)
        st.plotly_chart(C(px.line(f.groupby("order_date")[metric].sum().reset_index(), x="order_date", y=metric, title=f"Total {metric} — all categories")), use_container_width=True)
    with gt3:
        st.caption(f"Showing first 500 of {len(f):,} filtered records. Download exports the full filtered set.")
        st.dataframe(f.head(500), use_container_width=True, height=420)
        st.download_button("⬇ Download full filtered dataset (CSV)", f.to_csv(index=False), "cortexora_filtered.csv")
elif page == "Demand Forecasting":
    page_intro()
    top = st.columns([2,1,1])
    cat = top[0].selectbox("Category", sorted(products.category.unique()))
    horizon = top[1].slider("Forecast horizon (weeks)", 4, 16, 8); review = top[2].slider("Inventory review period (days)", 7, 60, 30)
    s = weekly_series(df, cat, products); ev = evaluate(s); fc = forecast_next(s, horizon)
    mae_delta = ev["seasonal_naive"]["WAPE"] - ev["moving_average_4w"]["WAPE"]
    kpi_cards([("Model WAPE (hold-out)", f"{ev['moving_average_4w']['WAPE']:.1%}", "moving-average 4w, chronological test"),
               ("Seasonal-naive WAPE", f"{ev['seasonal_naive']['WAPE']:.1%}", f"model is {'better' if mae_delta>0 else 'NOT better'} by {abs(mae_delta):.1%}"),
               ("Test volume", f"{ev['test_actual_total']:,.0f} units", f"train ended {ev['train_end']}"),
               ("Next-4-weeks outlook", f"{fc.forecast.head(4).sum():,.0f} units", f"{cat} · 80% interval shown")])
    ft1, ft2, ft3 = st.tabs(["🔮 Forecast", "🎯 Accuracy vs baseline", "📦 Inventory reorder plan"])
    with ft1:
        import plotly.graph_objects as go
        hist = s.reset_index(); hist.columns = ["week","actual"]
        fig = go.Figure()
        fig.add_scatter(x=fc.week, y=fc.upper, line=dict(width=0), showlegend=False)
        fig.add_scatter(x=fc.week, y=fc.lower, fill="tonexty", fillcolor="rgba(56,189,248,.18)", line=dict(width=0), name="80% interval")
        fig.add_scatter(x=hist.week.tail(40), y=hist.actual.tail(40), mode="lines", name="Actual demand", line=dict(color="#e8eef6", width=2))
        fig.add_scatter(x=fc.week, y=fc.forecast, mode="lines+markers", name="Forecast", line=dict(color="#38bdf8", width=3))
        st.plotly_chart(C(fig, 400).update_layout(title=f"{cat} — weekly demand: history, forecast & 80% interval"), use_container_width=True)
        st.dataframe(fc.assign(week=fc.week.dt.date), use_container_width=True)
        st.caption("Estimates, not actuals. Interval assumes roughly normal weekly variation around the 4-week moving average.")
    with ft2:
        evd = pd.DataFrame({m: ev[m] for m in ["moving_average_4w","seasonal_naive"]}).T.rename(index={"moving_average_4w":"CORTEXORA moving-average (4w)","seasonal_naive":"Seasonal-naive baseline"})
        st.dataframe(evd.style.highlight_min(axis=0, color="#14401f"), use_container_width=True)
        st.info("Read this before trusting the forecast: errors are measured on a chronological hold-out the model never saw. If the model did not beat the baseline, the chart above should not drive purchasing.")
    with ft3:
        st.caption(f"Forecast-based plan · 95% service level (z=1.65) · review period {review} days · costs at unit cost")
        stats = daily_demand_stats(df)
        stock = inv.merge(products[["product_id","category","unit_cost","list_price"]], on="product_id").merge(stats, on="product_id", how="left").fillna(0)
        plan = reorder_plan(stock, review_days=review)
        risk_counts = plan.stockout_risk.value_counts().to_dict()
        kpi_cards([("Products at high stockout risk", f"{risk_counts.get('High',0)}", "act this cycle"), ("Units to reorder", f"{plan.recommended_reorder_qty.sum():,}", "across all products"), ("Estimated order cost", f"${plan.estimated_order_cost.sum():,.0f}", "at current unit cost")], st.columns(3))
        st.dataframe(plan[["product_id","category","stock_on_hand","forecast_daily","lead_time_days","safety_stock","recommended_reorder_qty","estimated_order_cost","stockout_risk"]], use_container_width=True, height=420)
        st.download_button("⬇ Download reorder plan (CSV)", plan.to_csv(index=False), "reorder_plan.csv")
elif page == "Pricing & Profit Optimization":
    page_intro()
    st.info("Elasticity here is **your assumption**, not an estimated causal effect. Outputs are scenarios for discussion — not predictions, and not pricing advice proven by this data.")
    left, right = st.columns([1, 1.4])
    with left:
        with st.container(border=True):
            st.markdown("#### 🎛️ Scenario controls")
            pname = st.selectbox("Product", products.product_name); prow = products[products.product_name==pname].iloc[0]
            chg = st.slider("Price change %", -30, 30, 10); elas = st.slider("Assumed price elasticity", -3.0, -0.1, -1.2, step=0.1)
            fixed = st.number_input("Monthly fixed cost to cover ($)", value=10000.0, step=1000.0)
    sold = items[items.product_id==prow.product_id]; base_q = sold.qty.sum(); base_rev = (sold.qty*sold.unit_price*(1-sold.discount)).sum()
    new_q = base_q*(1+elas*chg/100); new_price = prow.list_price*(1+chg/100); new_rev = new_q*new_price
    new_profit = new_q*(new_price-prow.unit_cost); base_profit = base_rev - sold.qty.mul(sold.unit_cost).sum()
    be = breakeven_units(fixed, prow.list_price, prow.unit_cost)
    with right:
        kpi_cards([("Scenario revenue", f"${new_rev:,.0f}", f"{new_rev/base_rev-1:+.1%} vs observed"), ("Scenario profit", f"${new_profit:,.0f}", f"{new_profit/base_profit-1:+.1%} vs observed"), ("Scenario volume", f"{new_q:,.0f} units", f"from {base_q:,} at elasticity {elas}")], st.columns(3))
        sweep = pd.DataFrame([dict(price_change=c, revenue=base_q*(1+elas*c/100)*prow.list_price*(1+c/100)) for c in range(-30, 31, 2)])
        fig = px.line(sweep, x="price_change", y="revenue", title=f"Revenue across price changes (elasticity {elas}) — marker = your scenario")
        fig.add_scatter(x=[chg], y=[new_rev], mode="markers", marker=dict(size=14, color="#fbbf24"), name="Your scenario")
        st.plotly_chart(C(fig), use_container_width=True)
    pt1, pt2 = st.tabs(["🏷️ Discount effectiveness (observed)", "⚖️ Break-even"])
    with pt1:
        st.caption("Observed association only: discounted baskets differ in many ways. This does **not** estimate what a discount *causes* — use the Experiments Lab for that.")
        disc = discount_effectiveness(f); st.dataframe(disc, use_container_width=True)
        st.plotly_chart(C(px.bar(disc, x="discount_bucket", y="revenue", color="margin", color_continuous_scale="RdYlGn", title="Revenue by discount depth (colour = margin)")), use_container_width=True)
    with pt2:
        st.write(f"**{pname}** · list price ${prow.list_price:,.2f} · unit cost ${prow.unit_cost:,.2f} · contribution **${prow.list_price-prow.unit_cost:,.2f}/unit**")
        st.metric("Break-even volume for the fixed cost above", "Never — contribution ≤ $0" if be == float("inf") else f"{be:,.0f} units")
elif page == "Customer Intelligence":
    page_intro(); r = rfm(orders, items)
    from cortexora.models.churn import build_dataset, train_and_evaluate, predict_risk
    @st.cache_resource
    def _train():
        cutoff = pd.to_datetime(orders.order_date).max() - pd.Timedelta(days=90)
        data = build_dataset(orders, items, cutoff)
        return train_and_evaluate(data), data
    try:
        result, data = _train(); rep = result["report"]; risk = predict_risk(result["model"], data)
        churned = int((data.churn == 1).sum()); high_risk = int((risk.risk_band.astype(str) == "High").sum())
        ct1, ct2, ct3 = st.tabs(["🧩 Segments (RFM)", "🤖 Churn model", "🚨 Retention worklist"])
        with ct1:
            kpi_cards([("Customers", f"{len(r):,}", "in warehouse"), ("Active", f"{int((r.segment.astype(str)=='Active').sum()):,}", "ordered in last 90d"), ("At risk", f"{int((r.segment.astype(str)=='At risk').sum()):,}", "91–180d since last order"), ("Churned (heuristic)", f"{int((r.segment.astype(str).str.startswith('Churned')).sum()):,}", ">180d — heuristic, not the model")])
            a, b = st.columns(2)
            a.plotly_chart(C(px.histogram(r, x="segment", color="segment", title="Customers by RFM segment")), use_container_width=True)
            b.plotly_chart(C(px.scatter(r, x="recency_days", y="monetary", size="frequency", color="segment", title="Recency vs value (bubble = frequency)")), use_container_width=True)
            st.dataframe(r.sort_values("monetary", ascending=False).head(100), use_container_width=True, height=360)
        with ct2:
            st.caption("Label: **no purchase in the 90 days after cutoff** (a proxy — retail has no cancellation event). Trained on synthetic demo data: these metrics validate the pipeline, not real-world accuracy. Full detail: docs/06_MODEL_CARD_CHURN.md.")
            best = rep["results"][rep["best_model"]]; base_ = rep["results"]["baseline_majority"]
            kpi_cards([("Best model", rep["best_model"].replace("_"," "), f"of {rep['n_customers']} customers"), ("ROC-AUC", f"{best['roc_auc']:.2f}", f"baseline {base_['roc_auc']:.2f}"), ("PR-AUC", f"{best['pr_auc']:.2f}", f"baseline {base_['pr_auc']:.2f}"), ("Observed churn rate", f"{rep['churn_rate']:.1%}", f"hold-out n={rep['test_size']}")])
            a, b = st.columns(2)
            a.dataframe(pd.DataFrame(rep["results"]).T, use_container_width=True)
            b.plotly_chart(C(px.bar(pd.Series(rep["feature_importance"]).reset_index(), x="index", y=0, title="What the model leans on (explanation, not causation)")).update_xaxes(title="feature").update_yaxes(title="importance"), use_container_width=True)
        with ct3:
            kpi_cards([("High-risk customers", f"{high_risk}", "predicted probability > 66%"), ("Already churned (label)", f"{churned}", "no order in the 90d window"), ("Worklist size", f"{min(50, len(risk))}", "exportable below")], st.columns(3))
            st.dataframe(risk.head(50), use_container_width=True, height=420)
            st.download_button("⬇ Download full risk list (CSV)", risk.to_csv(index=False), "churn_risk.csv")
            st.caption("Act human-first: review before contacting anyone. A prediction is a prioritisation aid, not a verdict on a customer.")
    except ValueError as e: st.error(str(e))
elif page == "Marketing Performance":
    page_intro(); st.caption("CAC is a spend/conversions proxy. ROAS is not shown: no attribution join exists in this data — attributed ≠ incremental.")
    mm = marketing_metrics(mkt)
    kpi_cards([("Total spend", f"${mm.spend.sum():,.0f}", f"{mkt.spend_date.nunique()} weekly flights"), ("Conversions", f"{mm.conversions.sum():,}", "all channels"), ("Blended CAC (proxy)", f"${mm.spend.sum()/max(mm.conversions.sum(),1):,.2f}", "spend / conversion"), ("Best CAC channel", str(mm.loc[mm.cac_proxy.idxmin(),'channel']), f"${mm.cac_proxy.min():,.2f} per conversion")])
    mt1, mt2, mt3 = st.tabs(["📊 Channels", "🎯 Budget optimizer", "🧪 MMM readiness gate"])
    with mt1:
        a, b = st.columns(2)
        a.plotly_chart(C(px.bar(mm, x="channel", y="spend", color="cac_proxy", color_continuous_scale="RdYlGn_r", title="Spend by channel (colour = CAC, lower is greener)")), use_container_width=True)
        b.plotly_chart(C(px.bar(mm, x="channel", y="conversion_rate", title="Conversion rate by channel")), use_container_width=True)
        st.dataframe(mm, use_container_width=True)
    with mt2:
        st.caption("Fitted diminishing-returns response curves (conversions = a·spend^b). Scenarios from an associational fit — **not** causal incrementality.")
        budget = st.slider("Total weekly budget ($)", 500, 10000, 3300)
        opt = optimize_budget(mkt, total_budget=float(budget)); st.caption(opt.get("note",""))
        if "expected_gain_pct" in opt:
            kpi_cards([("Expected conversion change", f"{opt['expected_gain_pct']:+.1f}%", "same total budget, reallocated"), ("Reliable channels", f"{int(opt['curves'].reliable.sum())} / {len(opt['curves'])}", "R² and elasticity gates passed")], st.columns(2))
            comp = pd.DataFrame({"channel": list(opt["allocation"]), "current": [opt["current_allocation"][c] for c in opt["allocation"]], "optimized": list(opt["allocation"].values())})
            a, b = st.columns([1.3, 1])
            a.plotly_chart(C(px.bar(comp, x="channel", y=["current","optimized"], barmode="group", title="Current vs optimized weekly allocation")), use_container_width=True)
            b.dataframe(opt["curves"], use_container_width=True)
    with mt3:
        gate = mmm_readiness(mkt, has_revenue_outcome=False); st.dataframe(gate, use_container_width=True)
        if gate.Met.all(): st.success("All checks pass — MMM fitting is enabled.")
        else: st.warning("**MMM is NOT fitted** — the checks above fail. An unidentifiable model shown confidently is worse than no model. Needed: a revenue outcome joinable to weekly channel spend, plus external controls (price/promo/seasonality). The budget optimizer is the honest alternative on this data.")
elif page == "Experiments & Causal Lab":
    page_intro()
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
    page_intro()
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
    page_intro()
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
    kpi_cards([("⏳ Pending", f"{counts.get('pending',0)}", "awaiting your review"), ("✅ Approved", f"{counts.get('approved',0)}", "in flight"), ("⏸️ Deferred", f"{counts.get('deferred',0)}", "revisit later"), ("📏 Measured", f"{counts.get('measured',0)}", "outcome recorded"), ("🚫 Rejected", f"{counts.get('rejected',0)}", "closed")])
    owner = st.text_input("Decision owner (recorded on approve/record)", value="", placeholder="e.g. Logesh — accountability is part of the audit trail")
    STATUS_STYLE = {"pending": ("⏳","#fbbf24"), "approved": ("✅","#34d399"), "rejected": ("🚫","#fb7185"), "deferred": ("⏸️","#a5b4fc"), "measured": ("📏","#38bdf8")}
    for r in dec.itertuples():
        icon_, colour = STATUS_STYLE.get(r.status, ("•","#9db4d4"))
        with st.container(border=True):
            due = ""
            if pd.notna(r.decided_at) and pd.notna(r.measurement_period_days):
                due = f" · outcome due {(pd.Timestamp(r.decided_at) + pd.Timedelta(days=int(r.measurement_period_days))).date()}"
            st.markdown(f"<div class='cx-rec'><b style='color:#fff'>{icon_} {r.recommendation_id} · {r.area}</b> — {r.problem} → <b style='color:#7dd3fc'>{r.action}</b><br><span class='meta'>Evidence: {r.evidence} · Expected impact ${r.expected_impact:,.0f} · Priority {r.priority} · Status <b style='color:{colour}'>{r.status}</b>{due}</span></div>", unsafe_allow_html=True)
            if r.area == "Pricing" and r.status == "pending":
                st.caption("↳ Before acting, design this as a test in **Experiments & Causal Lab** so the outcome is causal, not anecdotal.")
            if r.status in ("pending","deferred"):
                b = st.columns(3)
                if b[0].button("✅ Approve", key=r.recommendation_id+"a"): set_status(r.recommendation_id,"approved",DB_PATH,owner); st.rerun()
                if b[1].button("🚫 Reject", key=r.recommendation_id+"r"): set_status(r.recommendation_id,"rejected",DB_PATH,owner); st.rerun()
                if b[2].button("⏸️ Defer", key=r.recommendation_id+"d"): set_status(r.recommendation_id,"deferred",DB_PATH,owner); st.rerun()
            if r.status == "approved":
                with st.expander(f"📏 Record actual outcome — {r.recommendation_id}"):
                    actual = st.number_input("Actual outcome (same units as expected impact, $)", key=r.recommendation_id+"act", value=float(r.expected_impact))
                    note = st.text_input("How was it measured? (source, period, caveats)", key=r.recommendation_id+"note")
                    if st.button("Record outcome", key=r.recommendation_id+"rec"):
                        if not note: st.error("A measurement note is required — an outcome without a source is not evidence.")
                        else:
                            try: record_outcome(r.recommendation_id, actual, note, DB_PATH, owner); st.rerun()
                            except ValueError as e: st.error(str(e))
            if r.status == "measured":
                var = (r.actual_outcome - r.expected_impact) / abs(r.expected_impact) * 100 if r.expected_impact else 0
                st.caption(f"📏 Measured: actual ${r.actual_outcome:,.0f} vs expected ${r.expected_impact:,.0f} ({var:+.1f}%) — {r.outcome_note}")
    st.subheader("Outcome tracking — did our decisions work?")
    s = outcome_summary(dec)
    if s["measured"] == 0:
        st.info("No measured outcomes yet. Approve a recommendation, act on it, wait its measurement period, then record the actual outcome above. CORTEXORA never invents outcome data.")
    else:
        m = st.columns(3); m[0].metric("Measured decisions", s["measured"]); m[1].metric("Median |variance| vs expected", f"{s['median_abs_variance_pct']:.1f}%"); m[2].metric("Within ±20% of expected", f"{s['within_20pct']:.0%}")
        det = s["detail"]
        st.plotly_chart(C(px.bar(det, x="recommendation_id", y="variance_pct", color="area", title="Outcome variance vs expectation (%) — calibration of the engine estimates")), use_container_width=True)
        st.dataframe(s["by_area"], use_container_width=True)
        st.dataframe(det[["recommendation_id","area","expected_impact","actual_outcome","variance_pct","owner","outcome_note"]], use_container_width=True)
        st.caption("Persistent large positive/negative bias by area means that detector's impact estimates are mis-calibrated — adjust its confidence/assumptions, don't just celebrate or panic over one result.")
    st.subheader("Decision history (audit log)")
    st.dataframe(dec, use_container_width=True)
    st.download_button("Download decision history CSV", dec.to_csv(index=False), "cortexora_decision_history.csv")

elif page == "Reports":
    page_intro()
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
    page_intro()
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
    page_intro()
    st.caption("Three different things, never conflated: **data drift ≠ prediction drift ≠ measured performance degradation**. Only the last — computed on later *labelled* data — is evidence about accuracy.")
    from cortexora.monitoring.quality import run_all
    from cortexora.monitoring.drift import drift_report, performance_comparison
    mon1, mon2, mon3 = st.tabs(["🏗️ Pipeline & data quality", "🌊 Drift", "🤖 Model performance"])
    with mon1:
        try:
            runs = load_table("pipeline_runs").sort_values("run_id", ascending=False)
            ok = int((runs.status == "success").sum()); bad = int((runs.status != "success").sum())
            last_ok = runs[runs.status=="success"].finished_at.max()
            kpi_cards([("Pipeline runs", f"{len(runs)}", f"{ok} succeeded · {bad} failed/blocked"), ("Last successful run", str(last_ok)[:16], "warehouse load"), ("Data current to", str(orders.order_date.max()), "end of synthetic dataset")], st.columns(3))
            st.dataframe(runs.head(10), use_container_width=True)
        except Exception: st.info("No pipeline runs logged yet — run `python scripts/run_etl.py`.")
        frames = {tb: load_table(tb) for tb in ["orders","order_items","customers","products"]}
        q = run_all(frames)
        fails = int((q.status=="FAIL").sum()); warns = int((q.status=="WARN").sum())
        if fails: st.error(f"{fails} FAIL check(s) — analytical outputs should not be trusted until resolved.")
        elif warns: st.warning(f"All hard checks pass; {warns} warning(s) to review.")
        else: st.success("All data-quality checks pass.")
        st.dataframe(q, use_container_width=True)
    with mon2:
        mid, end = df.order_date.min() + pd.Timedelta(days=540), df.order_date.max()
        ref, cur = df[df.order_date <= mid], df[df.order_date > end - pd.Timedelta(days=180)]
        dr = drift_report(ref, cur, ["qty","unit_price","discount","revenue"])
        worst = dr.iloc[0] if len(dr) else None
        kpi_cards([("Features tracked", f"{len(dr)}", "first 18m vs last 6m"), ("Highest PSI", f"{worst.psi:.3f}" if worst is not None else "—", f"{worst.feature}: {worst.status}" if worst is not None else "")], st.columns(2))
        st.dataframe(dr, use_container_width=True)
        st.plotly_chart(C(px.bar(dr, x="feature", y="psi", color="status", title="PSI by feature (0.10 = watch · 0.25 = investigate)")), use_container_width=True)
        st.caption("A shift is a prompt to investigate, not proof the model broke. Drift alone never proves degradation.")
    with mon3:
        st.caption("Train on an earlier cohort, score a later labelled cohort — the only honest way to detect degradation before it hurts.")
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
            kpi_cards([("Reference PR-AUC", f"{comp['reference']:.3f}", "hold-out, earlier cohort"), ("Later-period PR-AUC", f"{comp['current']:.3f}", delta_html(comp["delta"]*100, "absolute change (pp x100)")), ("Degraded?", "YES — investigate" if comp["degraded"] else "No", "threshold −0.05 PR-AUC"), ("Calibration gap", f"{cur_metrics['mean_predicted_probability']-cur_metrics['observed_churn_rate']:+.1%}", "predicted vs observed churn")])
            st.write(comp["note"])
            st.write(f"Later cohort: {len(cur_data)} customers · observed churn {cur_metrics['observed_churn_rate']:.1%} vs mean predicted {cur_metrics['mean_predicted_probability']:.1%}.")
            st.dataframe(pd.DataFrame({"reference_holdout": ref_metrics, "later_period": {kk: cur_metrics[kk] for kk in ref_metrics}}), use_container_width=True)
            import json, pathlib
            art = pathlib.Path("cortexora/models/artifacts/churn_evaluation.json")
            if art.exists():
                meta = json.loads(art.read_text()); st.caption(f"Registered artifact: {meta.get('model_version','?')} · trained {meta.get('trained_at','?')} · data cutoff {meta.get('data_cutoff','?')} · {meta.get('training_data','')}")
        except ValueError as e: st.error(str(e))

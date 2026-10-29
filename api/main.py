"""CORTEXORA FastAPI adapter — exposes the EXISTING Python analytics over HTTP.
No business logic is reimplemented here; every handler delegates to cortexora.*
or web.server computations. Run: .venv/bin/uvicorn api.main:app --port 8000"""
from __future__ import annotations
import io, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from web.server import dashboard as _dashboard, chat as _chat, DF, ORDERS, ITEMS, PRODUCTS, INV, MKT
from cortexora.config import DB_PATH
from cortexora.analytics.metrics import kpis, period_compare, marketing_metrics
from cortexora.decision_engine.engine import load_decisions, set_status, record_outcome, outcome_summary
from cortexora.pipelines.etl import load_table

app = FastAPI(title="CORTEXORA API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], allow_methods=["*"], allow_headers=["*"])
MODE = "demo-synthetic"

def rec(df, n=200):
    return json.loads(df.head(n).to_json(orient="records"))

@app.get("/api/health")
def health(): return {"status": "ok", "mode": MODE, "records": int(len(DF)), "data_through": str(DF.order_date.max().date())}

@app.get("/api/dashboard")
def dashboard(days: int = 10000, metric: str = "Revenue", gran: str = "Weekly", breakdown: str = "Total",
              cats: str = "", regs: str = "", chans: str = ""):
    q = {"days": [str(days)], "metric": [metric], "gran": [gran], "breakdown": [breakdown]}
    if cats: q["cats"] = [cats]
    if regs: q["regs"] = [regs]
    if chans: q["chans"] = [chans]
    out = _dashboard(q); out["mode"] = MODE; return out

@app.get("/api/growth")
def growth():
    by_cat = DF.groupby("category").agg(revenue=("revenue", "sum"), profit=("profit", "sum"), orders=("order_id", "nunique"), units=("qty", "sum")).reset_index()
    by_cat["margin"] = by_cat.profit / by_cat.revenue
    by_reg = DF.groupby("region").agg(revenue=("revenue", "sum"), profit=("profit", "sum")).reset_index()
    by_reg["margin"] = by_reg.profit / by_reg.revenue
    return {"mode": MODE, "kpis": kpis(DF), "period_compare": rec(period_compare(DF), 20),
            "by_category": rec(by_cat), "by_region": rec(by_reg),
            "products": dashboard()["products"]}

@app.get("/api/forecast")
def forecast(category: str = "Electronics", horizon: int = 8):
    from cortexora.models.forecasting import weekly_series, evaluate, forecast_next
    from cortexora.optimization.optimize import daily_demand_stats, reorder_plan
    s = weekly_series(DF, category, PRODUCTS); ev = evaluate(s); fc = forecast_next(s, horizon)
    stats = daily_demand_stats(DF)
    stock = INV.merge(PRODUCTS[["product_id", "category", "unit_cost", "list_price"]], on="product_id").merge(stats, on="product_id", how="left").fillna(0)
    plan = reorder_plan(stock)
    hist = s.tail(52)
    return {"mode": MODE, "category": category, "categories": sorted(PRODUCTS.category.unique()),
            "evaluation": ev, "forecast": [{"week": str(w.date()), "forecast": float(r.forecast), "lower": float(r.lower), "upper": float(r.upper)} for w, r in zip(fc.week, fc.itertuples())],
            "history": [{"week": str(w.date()), "actual": float(v)} for w, v in hist.items()],
            "reorder_plan": rec(plan[["product_id", "category", "stock_on_hand", "forecast_daily", "lead_time_days", "recommended_reorder_qty", "estimated_order_cost", "stockout_risk"]], 50)}

@app.get("/api/customers")
def customers():
    from cortexora.models.forecasting import rfm
    r = rfm(ORDERS, ITEMS)
    art = Path("cortexora/models/artifacts/churn_evaluation.json")
    return {"mode": MODE, "summary": {"customers": int(len(r)), "active": int((r.segment.astype(str) == "Active").sum()),
            "at_risk": int((r.segment.astype(str) == "At risk").sum()), "churned_heuristic": int(r.segment.astype(str).str.startswith("Churned").sum()),
            "repeat_rate": float((r.frequency > 1).mean()), "avg_clv": float(r.clv_simple.mean())},
            "segments": rec(r.segment.astype(str).value_counts().rename_axis("segment").reset_index(name="customers"), 10),
            "customers_table": rec(r.sort_values("monetary", ascending=False), 500),
            "churn_model": json.loads(art.read_text()) if art.exists() else None}

@app.get("/api/marketing")
def marketing(budget: float = 3300):
    from cortexora.optimization.optimize import optimize_budget
    mm = marketing_metrics(MKT); opt = optimize_budget(MKT, total_budget=budget)
    return {"mode": MODE, "channels": rec(mm), "optimizer": {k: v for k, v in opt.items() if k != "curves"},
            "curves": rec(opt["curves"]) if "curves" in opt else []}

@app.get("/api/pricing")
def pricing(product: str = "", change: float = 10, elasticity: float = -1.2):
    from cortexora.optimization.optimize import discount_effectiveness, breakeven_units
    p = PRODUCTS[PRODUCTS.product_name == product].iloc[0] if product and (PRODUCTS.product_name == product).any() else PRODUCTS.iloc[0]
    sold = ITEMS[ITEMS.product_id == p.product_id]
    base_q, base_rev = float(sold.qty.sum()), float((sold.qty * sold.unit_price * (1 - sold.discount)).sum())
    new_rev = base_q * (1 + elasticity * change / 100) * float(p.list_price) * (1 + change / 100)
    return {"mode": MODE, "products": list(PRODUCTS.product_name), "product": {"name": str(p.product_name), "list_price": float(p.list_price), "unit_cost": float(p.unit_cost)},
            "scenario": {"change_pct": change, "elasticity": elasticity, "observed_revenue": base_rev, "scenario_revenue": float(new_rev), "delta_pct": float(new_rev / base_rev - 1) * 100 if base_rev else 0,
                         "label": "Assumption-based scenario — elasticity is a user input, not an estimated causal effect."},
            "breakeven_units_at_10000_fixed": breakeven_units(10000, float(p.list_price), float(p.unit_cost)),
            "discount_effectiveness": rec(discount_effectiveness(DF))}

@app.get("/api/mmm")
def mmm():
    from cortexora.analytics.experiments import mmm_readiness
    g = mmm_readiness(MKT, has_revenue_outcome=False)
    return {"mode": MODE, "fitted": False, "readiness": rec(g),
            "note": "MMM fitting stays disabled until a revenue outcome joinable to weekly channel spend and external controls exist."}

@app.get("/api/experiments")
def experiments():
    from cortexora.analytics.experiments import ab_conversion, required_sample_size, srm_check
    return {"mode": MODE,
            "example_observed": ab_conversion(1200, 156, 1200, 132) | {"name": "Demo A/B example (labelled synthetic counts)", "srm": srm_check(1200, 1200)},
            "planning": {"baseline": 0.11, "mde_abs": 0.02, "per_group_n": required_sample_size(0.11, 0.02)}}

@app.get("/api/decisions")
def decisions():
    dec = load_decisions(DB_PATH)
    return {"mode": MODE, "decisions": rec(dec, 200) if len(dec) else [], "outcome_summary": {k: v for k, v in outcome_summary(dec).items() if k not in ("detail", "by_area")}}

class StatusIn(BaseModel):
    status: str; owner: str = ""

@app.post("/api/decisions/{rid}/status")
def decision_status(rid: str, body: StatusIn):
    if body.status not in ("approved", "rejected", "deferred"): raise HTTPException(400, "status must be approved/rejected/deferred")
    try: set_status(rid, body.status, DB_PATH, body.owner)
    except ValueError as e: raise HTTPException(400, str(e))
    return {"ok": True, "id": rid, "status": body.status}

class OutcomeIn(BaseModel):
    actual: float; note: str; owner: str = ""

@app.post("/api/decisions/{rid}/outcome")
def decision_outcome(rid: str, body: OutcomeIn):
    try: record_outcome(rid, body.actual, body.note, DB_PATH, body.owner)
    except ValueError as e: raise HTTPException(400, str(e))
    return {"ok": True, "id": rid, "status": "measured"}

@app.get("/api/health-data")
def health_data():
    from cortexora.monitoring.quality import run_all
    from cortexora.monitoring.drift import drift_report
    frames = {t: load_table(t) for t in ["orders", "order_items", "customers", "products"]}
    mid, end = DF.order_date.min() + pd.Timedelta(days=540), DF.order_date.max()
    try: runs = rec(load_table("pipeline_runs").sort_values("run_id", ascending=False), 20)
    except Exception: runs = []
    return {"mode": MODE, "quality": rec(run_all(frames), 50), "quality_fails": int((run_all(frames).status == "FAIL").sum()),
            "drift": rec(drift_report(DF[DF.order_date <= mid], DF[DF.order_date > end - pd.Timedelta(days=180)], ["qty", "unit_price", "discount", "revenue"])),
            "pipeline_runs": runs}

@app.get("/api/datasources")
def datasources():
    out = []
    for t in ["customers", "products", "orders", "order_items", "inventory_snapshots", "marketing_spend", "decisions"]:
        try:
            d = load_table(t); out.append({"table": t, "rows": int(len(d)), "columns": list(d.columns)})
        except Exception as e: out.append({"table": t, "rows": 0, "columns": [], "error": str(e)})
    return {"mode": MODE, "sources": out, "warehouse": str(DB_PATH)}

@app.post("/api/upload/analyse")
async def upload_analyse(file: UploadFile = File(...), cost_ratio: float = 0.55):
    from cortexora.pipelines.upload import guess_mapping, transform
    raw_bytes = await file.read()
    try: raw = pd.read_csv(io.BytesIO(raw_bytes))
    except Exception: raw = pd.read_csv(io.BytesIO(raw_bytes), encoding="latin-1")
    try:
        frames, report = transform(raw, guess_mapping(list(raw.columns)), cost_ratio)
    except ValueError as e: raise HTTPException(422, str(e))
    from cortexora.analytics.metrics import enrich
    d = enrich(frames["orders"], frames["order_items"]).merge(frames["products"][["product_id", "category"]], on="product_id")
    return {"mode": MODE, "report": report, "kpis": kpis(d),
            "by_category": rec(d.groupby("category").agg(revenue=("revenue", "sum"), profit=("profit", "sum")).reset_index()),
            "note": "Analysed in-memory only. To make it the live warehouse, use the Streamlit Upload & Analyse page's load step (same transform, ETL-gated)."}

@app.get("/api/reports/executive")
def executive_report():
    from cortexora.reports.report import generate_markdown_report
    from cortexora.models.forecasting import weekly_series, evaluate
    art = Path("cortexora/models/artifacts/churn_evaluation.json")
    md = generate_markdown_report(DF, evaluate(weekly_series(DF, "Electronics", PRODUCTS)),
                                  json.loads(art.read_text()) if art.exists() else None, load_decisions(DB_PATH), "Next.js UI export")
    return {"mode": MODE, "markdown": md}

class ChatIn(BaseModel):
    question: str; page: object = ""

@app.post("/api/chat")
def chat(body: ChatIn):
    out = _chat(body.question)
    out["mode"] = "demo-assistant (deterministic, data-grounded — no LLM API configured)"
    out["page_context"] = body.page
    return out

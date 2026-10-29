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
    """Analyse ANY tabular CSV: detect columns by name AND content, verify the
    dataset, then run sales analysis + prediction as far as its structure
    honestly allows. Non-sales datasets get a profile + statistical summary
    instead of a hard failure."""
    from cortexora.pipelines.upload import (detect_mapping, profile_dataset, transform,
                                            parse_dates, _clean_num, _col_kind)
    raw_bytes = await file.read()
    raw = None
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            raw = pd.read_csv(io.BytesIO(raw_bytes), sep=None, engine="python", encoding=enc)
            if len(raw.columns) >= 1: break
        except Exception:
            raw = None
    if raw is None or raw.empty or len(raw.columns) == 0:
        raise HTTPException(422, "Could not read this file as a table. Upload a CSV with a header row.")
    raw.columns = [str(c).strip() for c in raw.columns]
    detected = detect_mapping(raw)
    profile = profile_dataset(raw, detected)
    mapping = {f: v["column"] for f, v in detected.items()}
    verification = {"dataset_type": profile["dataset_type"], "checks": profile["checks"],
                    "columns": profile["columns"], "mapping": detected,
                    "analysable_as_sales": profile["analysable_as_sales"]}

    if not profile["analysable_as_sales"]:
        # ---- generic dataset: verify + summarise, never fake a sales analysis ----
        numeric, categorical, correlations = [], [], []
        num_cols = {}
        for c in raw.columns:
            if _col_kind(raw[c]) == "numeric":
                v = _clean_num(raw[c]); num_cols[c] = v
                numeric.append({"column": str(c), "count": int(v.notna().sum()), "mean": float(v.mean()),
                                "median": float(v.median()), "min": float(v.min()), "max": float(v.max()),
                                "missing_pct": round(float(v.isna().mean() * 100), 1)})
            elif raw[c].dtype == object and raw[c].nunique() <= 20:
                categorical.append({"column": str(c),
                                    "top_values": [{"value": str(k)[:40], "rows": int(n)}
                                                   for k, n in raw[c].value_counts().head(5).items()]})
        keys = list(num_cols)
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                pair = pd.concat([num_cols[keys[i]], num_cols[keys[j]]], axis=1).dropna()
                if len(pair) > 3 and pair.iloc[:, 0].std() and pair.iloc[:, 1].std():
                    correlations.append({"a": str(keys[i]), "b": str(keys[j]),
                                         "correlation": round(float(pair.iloc[:, 0].corr(pair.iloc[:, 1])), 3),
                                         "note": "association only — not causation"})
        correlations.sort(key=lambda x: -abs(x["correlation"]))
        ts_note = None
        if profile["analysable_as_timeseries"] and detected["order_date"]["column"]:
            dcol = detected["order_date"]["column"]
            dates, _ = parse_dates(raw[dcol])
            ts_note = f"Date column detected ({dcol}): {int(dates.notna().sum())} parseable dates from {str(dates.min())[:10]} to {str(dates.max())[:10]}. Add a sales value column (price or total) to unlock trend + forecast."
        return {"kind": "generic", "mode": MODE, "verification": verification,
                "numeric_summary": numeric, "categorical_summary": categorical,
                "correlations": correlations[:8], "timeseries_note": ts_note,
                "note": "This file was verified and profiled, but no date + sales-value pair was detected, so sales KPIs and forecasting were not run. Rename columns or add a date and price/total column — detection also reads column contents, not just names."}

    try:
        frames, report = transform(raw, mapping, cost_ratio)
    except ValueError as e:
        raise HTTPException(422, str(e))
    from cortexora.analytics.metrics import enrich
    d = enrich(frames["orders"], frames["order_items"]).merge(frames["products"][["product_id", "category"]], on="product_id")
    d["month"] = d["order_date"].dt.to_period("M").astype(str)
    trend = rec(d.groupby("month").agg(revenue=("revenue", "sum"), profit=("profit", "sum"),
                                       units=("qty", "sum"), orders=("order_id", "nunique")).reset_index()
                .rename(columns={"month": "label"}))
    by_product = rec(d.groupby(["product_id", "product_name", "category"] if "product_name" in d else ["product_id", "category"])
                     .agg(revenue=("revenue", "sum"), profit=("profit", "sum"), units=("qty", "sum")).reset_index()
                     .sort_values("revenue", ascending=False).head(10))
    # --- prediction on the uploaded file's OWN series (units, or revenue for aggregates) ---
    forecast_block = None
    try:
        from cortexora.models.forecasting import weekly_series, evaluate, forecast_next
        if report.get("qty_is_assumed"):
            ws = d.set_index("order_date").resample("W")["revenue"].sum().asfreq("W").fillna(0)
            metric_name, unit_label = "revenue", "Revenue $"
        else:
            ws = weekly_series(d); metric_name, unit_label = "units", "Units"
        weeks = int(len(ws))
        avg_unit_revenue = float(d["revenue"].sum() / d["qty"].sum()) if d["qty"].sum() else 0.0
        if weeks >= 24:
            ev = evaluate(ws)
            fcdf = forecast_next(ws, 8)
            model_wape, base_wape = ev["moving_average_4w"]["WAPE"], ev["seasonal_naive"]["WAPE"]
            rows = [{"week": str(pd.Timestamp(r.week).date()), "forecast": float(r.forecast),
                     "lower": float(r.lower), "upper": float(r.upper),
                     "forecast_revenue": float(r.forecast if metric_name == "revenue" else r.forecast * avg_unit_revenue)}
                    for r in fcdf.itertuples()]
            forecast_block = {"available": True, "metric": metric_name, "weeks_of_history": weeks,
                              "history": [{"week": str(t.date()), "units": float(v)} for t, v in ws.tail(26).items()],
                              "forecast": rows,
                              "predicted_units_8w": float(fcdf["forecast"].sum()) if metric_name == "units" else None,
                              "predicted_revenue_8w": float(fcdf["forecast"].sum() if metric_name == "revenue" else fcdf["forecast"].sum() * avg_unit_revenue),
                              "model_wape": model_wape, "baseline_wape": base_wape,
                              "model_beats_baseline": bool(model_wape < base_wape),
                              "method": f"4-week moving average on weekly {metric_name} vs seasonal-naive baseline, chronological 12-week hold-out (WAPE)"}
        else:
            forecast_block = {"available": False, "metric": metric_name, "weeks_of_history": weeks,
                              "reason": f"Only {weeks} weekly periods in this file — at least ~24 are needed for a forecast with an honest hold-out evaluation. The analysis above still applies."}
    except Exception as e:
        forecast_block = {"available": False, "weeks_of_history": 0, "reason": f"Forecast unavailable for this file: {e}"}
    warnings = []
    if report.get("qty_is_assumed"): warnings.append("No quantity column detected — each row treated as one sale; unit-based metrics reflect row counts.")
    if report.get("price_is_derived"): warnings.append("Unit price derived from the line-total column ÷ quantity.")
    if report.get("product_is_fallback"): warnings.append("No product column detected — everything analysed as one combined series.")
    if report.get("date_note") and "assumed" in str(report["date_note"]): warnings.append(f"Dates: {report['date_note']}.")
    return {"kind": "sales", "mode": MODE, "report": report, "kpis": kpis(d), "trend": trend,
            "top_products": by_product, "forecast": forecast_block, "verification": verification,
            "warnings": warnings,
            "by_category": rec(d.groupby("category").agg(revenue=("revenue", "sum"), profit=("profit", "sum")).reset_index()),
            "note": "Analysed in-memory only. To make it the live warehouse, use the Streamlit Upload & Analyse page's load step (same transform, ETL-gated)."}

@app.post("/api/upload/multi")
async def upload_multi(files: list[UploadFile] = File(...), cost_ratio: float = 0.55):
    """Folder/batch upload: many files, many formats (CSV/TSV/Excel/JSON/
    Parquet/ZIP). Every file is verified and analysed; sales files are also
    combined. Bad members are reported per-file and never fail the batch."""
    from cortexora.pipelines.multi import analyse_batch
    payload = [(f.filename or "upload", await f.read()) for f in files]
    try:
        return {"mode": MODE, **analyse_batch(payload, cost_ratio)}
    except ValueError as e:
        raise HTTPException(422, str(e))

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

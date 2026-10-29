"""CORTEXORA Web — custom interactive UI server (stdlib only, no new deps).

Serves the bespoke dashboard in web/static/ and a JSON API backed by the
*same* analytics the Streamlit app uses (metrics layer, decision log, chatbot).
Run:  .venv/bin/python web/server.py   ->  http://localhost:8502
"""
from __future__ import annotations
import json, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd
from cortexora.analytics.metrics import enrich, kpis
from cortexora.pipelines.etl import load_table
from cortexora.decision_engine.engine import load_decisions
from cortexora.assistant.chatbot import answer_question
from cortexora.config import DB_PATH

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"

def _load():
    orders, items, products, inv, mkt = (load_table(t) for t in ["orders", "order_items", "products", "inventory_snapshots", "marketing_spend"])
    df = enrich(orders, items).merge(products[["product_id", "category", "product_name"]], on="product_id")
    return df, orders, items, products, inv, mkt

DF, ORDERS, ITEMS, PRODUCTS, INV, MKT = _load()

def reload_data():
    """Re-read the warehouse (after an uploaded dataset replaces it) so every
    dashboard/chat computation in this process uses the NEW data."""
    global DF, ORDERS, ITEMS, PRODUCTS, INV, MKT
    DF, ORDERS, ITEMS, PRODUCTS, INV, MKT = _load()
    return DF
METRIC_COL = {"Revenue": "revenue", "Profit": "profit", "Units": "qty"}

def dashboard(params: dict) -> dict:
    days = int(params.get("days", ["10000"])[0])
    metric = params.get("metric", ["Revenue"])[0]
    gran = params.get("gran", ["Weekly"])[0]
    breakdown = params.get("breakdown", ["Total"])[0]
    cats = params.get("cats", [",".join(sorted(DF.category.unique()))])[0].split(",")
    regs = params.get("regs", [",".join(sorted(DF.region.unique()))])[0].split(",")
    chans = params.get("chans", [",".join(sorted(DF.channel.unique()))])[0].split(",")
    end = DF.order_date.max()
    d = DF[DF.category.isin(cats) & DF.region.isin(regs) & DF.channel.isin(chans) & (DF.order_date > end - pd.Timedelta(days=days))]
    col = METRIC_COL.get(metric, "revenue")
    k = kpis(d) if len(d) else dict(revenue=0, profit=0, margin=0, orders=0, aov=0, units=0, customers=0)
    prior = DF[DF.category.isin(cats) & DF.region.isin(regs) & DF.channel.isin(chans)
               & DF.order_date.between(end - pd.Timedelta(days=2 * days), end - pd.Timedelta(days=days))]
    kp = kpis(prior) if len(prior) else dict(revenue=0, profit=0, orders=0)
    def delta(a, b): return round((a / b - 1) * 100, 1) if b else 0.0
    freq = {"Daily": "D", "Weekly": "W", "Monthly": "ME"}[gran]
    # trend, optionally split by a dimension
    if breakdown == "Total" or breakdown.lower() not in d:
        tr = d.set_index("order_date").resample(freq)[col].sum() if metric != "Orders" else d.set_index("order_date").resample(freq)["order_id"].nunique()
        trend = {"labels": [str(x.date()) for x in tr.index], "series": [{"name": metric, "data": [float(v) for v in tr.values]}]}
    else:
        dim = breakdown.lower()
        if metric == "Orders":
            tr = d.groupby([pd.Grouper(key="order_date", freq=freq), dim])["order_id"].nunique().reset_index()
        else:
            tr = d.groupby([pd.Grouper(key="order_date", freq=freq), dim])[col].sum().reset_index()
        labels = sorted(tr.order_date.dt.strftime("%Y-%m-%d").unique())
        series = [{"name": str(name), "data": [float(g.set_index(g.order_date.dt.strftime("%Y-%m-%d"))[col if metric != "Orders" else "order_id"].get(l, 0)) for l in labels]}
                  for name, g in tr.groupby(dim)]
        trend = {"labels": labels, "series": series}
    cat = d.groupby("category")[col if metric != "Orders" else "revenue"].sum().sort_values(ascending=False)
    reg = d.groupby("region")[col if metric != "Orders" else "revenue"].sum().sort_values(ascending=False)
    prod = (d.groupby(["product_name", "category"]).agg(revenue=("revenue", "sum"), profit=("profit", "sum"),
            units=("qty", "sum"), orders=("order_id", "nunique")).reset_index())
    prod["margin"] = prod.profit / prod.revenue.replace(0, pd.NA)
    prod = prod.sort_values("revenue", ascending=False).head(20)
    by_cat_rev = d.groupby("category").apply(lambda g: (g.revenue.sum(), g.profit.sum() / g.revenue.sum() if g.revenue.sum() else 0))
    low_margin_cat = min(by_cat_rev.items(), key=lambda kv: kv[1][1])[0] if len(by_cat_rev) else "—"
    return dict(
        kpis=dict(revenue=float(k["revenue"]), profit=float(k["profit"]), margin=float(k["margin"]),
                  orders=int(k["orders"]), aov=float(k["aov"]), units=int(k["units"]), customers=int(k["customers"]),
                  revenue_delta=delta(k["revenue"], kp["revenue"]), profit_delta=delta(k["profit"], kp["profit"]),
                  orders_delta=delta(k["orders"], kp["orders"])),
        trend=trend,
        categories=[{"name": n, "value": float(v)} for n, v in cat.items()],
        regions=[{"name": n, "value": float(v)} for n, v in reg.items()],
        products=prod.fillna(0).to_dict("records"),
        insights=dict(top_category=str(cat.index[0]) if len(cat) else "—", top_category_value=float(cat.iloc[0]) if len(cat) else 0,
                      top_region=str(reg.index[0]) if len(reg) else "—", margin_watch=str(low_margin_cat),
                      records=int(len(d)), data_through=str(end.date())))

def chat(question: str) -> dict:
    art = ROOT.parent / "cortexora" / "models" / "artifacts" / "churn_evaluation.json"
    ctx = dict(df=DF, orders=ORDERS, items=ITEMS, products=PRODUCTS, mkt=MKT, inv=INV,
               decisions=load_decisions(DB_PATH),
               churn_rep=json.loads(art.read_text()) if art.exists() else None)
    ans = answer_question(question, ctx)
    table = None
    if ans.get("table") is not None:
        table = ans["table"].head(8).astype(str).to_dict("records")
    return dict(text=ans["text"], navigate=ans.get("navigate"), table=table)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/api/dashboard":
            try: self._send(200, dashboard(parse_qs(u.query)))
            except Exception as e: self._send(500, {"error": str(e)})
        elif u.path == "/api/health":
            self._send(200, {"status": "ok", "records": int(len(DF))})
        else:
            f = STATIC / ("index.html" if u.path in ("/", "") else u.path.lstrip("/"))
            if f.is_file():
                ctype = {".html": "text/html", ".css": "text/css", ".js": "application/javascript"}.get(f.suffix, "text/plain")
                self._send(200, f.read_bytes(), ctype)
            else: self._send(404, {"error": "not found"})
    def do_POST(self):
        if urlparse(self.path).path == "/api/chat":
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            try: self._send(200, chat(str(body.get("question", ""))))
            except Exception as e: self._send(500, {"error": str(e), "text": "Something went wrong computing that answer."})
        else: self._send(404, {"error": "not found"})

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8502
    print(f"CORTEXORA Web on http://0.0.0.0:{port}  ({len(DF):,} records)")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()

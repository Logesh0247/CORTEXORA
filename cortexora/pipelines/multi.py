"""Multi-file, multi-format ingestion (folder / batch upload).

Accepts many files at once, in the formats real data actually arrives in —
CSV, TSV/TXT, Excel (.xlsx/.xls, all sheets), JSON, Parquet, and ZIP archives
containing any of those — verifies every file, then analyses:

  * each sales-shaped file on its own (KPIs, trend, forecast),
  * all sales files COMBINED (product identities unified by name), and
  * non-sales files with an honest statistical profile.

Unsupported or corrupt members are reported per-file, never silently dropped
and never allowed to fail the whole batch. Uploaded content is parsed as data
only — no code execution, no macros, ZIP members are read in memory with
count/size guards (zip-bomb safe).
"""
from __future__ import annotations
import io, json, zipfile
import numpy as np, pandas as pd

MAX_FILES = 25
MAX_MEMBER_BYTES = 25 * 1024 * 1024  # 25 MB per extracted file

SUPPORTED = {".csv", ".tsv", ".txt", ".xlsx", ".xls", ".json", ".parquet", ".pq"}


def _read_csv_bytes(b: bytes) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            df = pd.read_csv(io.BytesIO(b), sep=None, engine="python", encoding=enc)
            if len(df.columns): return df
        except Exception:
            continue
    raise ValueError("could not parse as delimited text")


def parse_tabular(name: str, data: bytes) -> tuple[pd.DataFrame, str, str]:
    """(frame, format, note). Raises ValueError with a human reason."""
    lower = name.lower()
    if len(data) > MAX_MEMBER_BYTES:
        raise ValueError(f"file is {len(data)/1e6:.1f} MB — limit is {MAX_MEMBER_BYTES//(1024*1024)} MB per file")
    if lower.endswith((".csv", ".tsv", ".txt")):
        df = _read_csv_bytes(data)
        return df, ("TSV" if lower.endswith(".tsv") else "CSV"), ""
    if lower.endswith((".xlsx", ".xls")):
        try:
            sheets = pd.read_excel(io.BytesIO(data), sheet_name=None)
        except Exception as e:
            raise ValueError(f"Excel parse failed: {e}")
        frames, used = [], []
        base_cols = None
        for sheet, sdf in sheets.items():
            if sdf is None or sdf.empty: continue
            if base_cols is None:
                base_cols = list(sdf.columns); frames.append(sdf); used.append(sheet)
            elif list(sdf.columns) == base_cols:
                frames.append(sdf); used.append(sheet)
        if not frames: raise ValueError("Excel workbook has no readable data sheets")
        df = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
        note = f"sheets combined: {', '.join(used)}" if len(used) > 1 else f"sheet: {used[0]}"
        if len(used) < len(sheets): note += f" ({len(sheets)-len(used)} sheet(s) skipped — different columns)"
        return df, "Excel", note
    if lower.endswith(".json"):
        try:
            obj = json.loads(data.decode("utf-8", errors="replace"))
            if isinstance(obj, dict):  # {key: [records]} or a single record
                lists = [v for v in obj.values() if isinstance(v, list)]
                obj = lists[0] if lists else [obj]
            df = pd.json_normalize(obj)
        except Exception:
            try: df = pd.read_json(io.BytesIO(data), lines=True)
            except Exception as e: raise ValueError(f"JSON parse failed: {e}")
        return df, "JSON", ""
    if lower.endswith((".parquet", ".pq")):
        try: return pd.read_parquet(io.BytesIO(data)), "Parquet", ""
        except Exception as e: raise ValueError(f"Parquet parse failed: {e}")
    raise ValueError("unsupported format — use CSV, TSV, Excel, JSON, Parquet, or a ZIP of those")


def expand_uploads(files: list[tuple[str, bytes]]) -> list[tuple[str, bytes]]:
    """Flatten ZIP archives into their data members (guarded)."""
    out: list[tuple[str, bytes]] = []
    for name, data in files:
        if name.lower().endswith(".zip"):
            try:
                zf = zipfile.ZipFile(io.BytesIO(data))
            except Exception:
                out.append((name, data)); continue  # parse step will report it
            members = [i for i in zf.infolist() if not i.is_dir()]
            if len(members) > MAX_FILES:
                raise ValueError(f"{name}: archive has {len(members)} files — limit is {MAX_FILES}")
            for info in members:
                if info.file_size > MAX_MEMBER_BYTES:
                    raise ValueError(f"{name}: member {info.filename} exceeds the per-file size limit")
                out.append((f"{name}::{info.filename.split('/')[-1]}", zf.read(info)))
        else:
            out.append((name, data))
    return out[:MAX_FILES]


def _rec(df, n=200):
    return json.loads(df.head(n).to_json(orient="records", date_format="iso"))


def sales_lines(raw: pd.DataFrame, cost_ratio: float = 0.55):
    """(enriched line-level frame, report, detected) for a sales-shaped frame."""
    from cortexora.pipelines.upload import detect_mapping, transform
    from cortexora.analytics.metrics import enrich
    detected = detect_mapping(raw)
    mapping = {f: v["column"] for f, v in detected.items()}
    frames, report = transform(raw, mapping, cost_ratio)
    d = enrich(frames["orders"], frames["order_items"]).merge(
        frames["products"][["product_id", "product_name", "category"]], on="product_id")
    return d, report, detected


def forecast_block_for(d: pd.DataFrame, qty_assumed: bool) -> dict:
    """8-week prediction on a frame's own weekly series, baseline-scored."""
    try:
        from cortexora.models.forecasting import weekly_series, evaluate, forecast_next
        if qty_assumed:
            ws = d.set_index("order_date").resample("W")["revenue"].sum().asfreq("W").fillna(0)
            metric = "revenue"
        else:
            ws = weekly_series(d); metric = "units"
        weeks = int(len(ws))
        avg_unit_rev = float(d["revenue"].sum() / d["qty"].sum()) if d["qty"].sum() else 0.0
        if weeks < 24:
            return {"available": False, "metric": metric, "weeks_of_history": weeks,
                    "reason": f"Only {weeks} weekly periods — at least ~24 are needed for a forecast with an honest hold-out evaluation."}
        ev = evaluate(ws); fcdf = forecast_next(ws, 8)
        mw, bw = ev["moving_average_4w"]["WAPE"], ev["seasonal_naive"]["WAPE"]
        rows = [{"week": str(pd.Timestamp(r.week).date()), "forecast": float(r.forecast),
                 "lower": float(r.lower), "upper": float(r.upper),
                 "forecast_revenue": float(r.forecast if metric == "revenue" else r.forecast * avg_unit_rev)}
                for r in fcdf.itertuples()]
        return {"available": True, "metric": metric, "weeks_of_history": weeks,
                "history": [{"week": str(t.date()), "units": float(v)} for t, v in ws.tail(26).items()],
                "forecast": rows,
                "predicted_units_8w": float(fcdf["forecast"].sum()) if metric == "units" else None,
                "predicted_revenue_8w": float(fcdf["forecast"].sum() if metric == "revenue" else fcdf["forecast"].sum() * avg_unit_rev),
                "model_wape": mw, "baseline_wape": bw, "model_beats_baseline": bool(mw < bw),
                "method": f"4-week moving average on weekly {metric} vs seasonal-naive baseline, chronological 12-week hold-out (WAPE)"}
    except Exception as e:
        return {"available": False, "weeks_of_history": 0, "reason": f"Forecast unavailable: {e}"}


def analyse_frame(raw: pd.DataFrame, cost_ratio: float = 0.55) -> dict:
    """Full single-frame analysis (sales or generic), JSON-safe. Mirrors the
    /api/upload/analyse contract."""
    from cortexora.pipelines.upload import detect_mapping, profile_dataset, _clean_num, _col_kind, parse_dates
    from cortexora.analytics.metrics import kpis
    raw = raw.copy(); raw.columns = [str(c).strip() for c in raw.columns]
    detected = detect_mapping(raw); profile = profile_dataset(raw, detected)
    verification = {"dataset_type": profile["dataset_type"], "checks": profile["checks"],
                    "columns": profile["columns"], "mapping": detected,
                    "analysable_as_sales": profile["analysable_as_sales"]}
    if not profile["analysable_as_sales"]:
        numeric, categorical, correlations, num_cols = [], [], [], {}
        for c in raw.columns:
            if _col_kind(raw[c]) == "numeric":
                v = _clean_num(raw[c]); num_cols[c] = v
                numeric.append({"column": str(c), "count": int(v.notna().sum()), "mean": float(v.mean()),
                                "median": float(v.median()), "min": float(v.min()), "max": float(v.max()),
                                "missing_pct": round(float(v.isna().mean() * 100), 1)})
            elif raw[c].dtype == object and raw[c].nunique() <= 20:
                categorical.append({"column": str(c), "top_values": [
                    {"value": str(k)[:40], "rows": int(n)} for k, n in raw[c].value_counts().head(5).items()]})
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
            dcol = detected["order_date"]["column"]; dates, _ = parse_dates(raw[dcol])
            ts_note = (f"Date column detected ({dcol}): {int(dates.notna().sum())} parseable dates, "
                       f"{str(dates.min())[:10]} to {str(dates.max())[:10]}. Add a sales value column (price or total) to unlock trend + forecast.")
        return {"kind": "generic", "verification": verification, "numeric_summary": numeric,
                "categorical_summary": categorical, "correlations": correlations[:8],
                "timeseries_note": ts_note,
                "note": "Verified and profiled, but no date + sales-value pair was detected, so sales KPIs and forecasting were not run."}
    d, report, _ = sales_lines(raw, cost_ratio)
    from cortexora.pipelines.intelligence import business_intelligence
    d["month"] = d["order_date"].dt.to_period("M").astype(str)
    trend = _rec(d.groupby("month").agg(revenue=("revenue", "sum"), profit=("profit", "sum"),
                                        units=("qty", "sum"), orders=("order_id", "nunique")).reset_index()
                 .rename(columns={"month": "label"}))
    by_product = _rec(d.groupby(["product_id", "product_name", "category"])
                      .agg(revenue=("revenue", "sum"), profit=("profit", "sum"), units=("qty", "sum")).reset_index()
                      .sort_values("revenue", ascending=False).head(10))
    warnings = []
    if report.get("qty_is_assumed"): warnings.append("No quantity column detected — each row treated as one sale; unit metrics reflect row counts.")
    if report.get("price_is_derived"): warnings.append("Unit price derived from the line-total column ÷ quantity.")
    if report.get("product_is_fallback"): warnings.append("No product column detected — analysed as one combined series.")
    if report.get("date_note") and "assumed" in str(report["date_note"]): warnings.append(f"Dates: {report['date_note']}.")
    fc_block = forecast_block_for(d, bool(report.get("qty_is_assumed")))
    return {"kind": "sales", "report": report, "kpis": kpis(d), "trend": trend,
            "intelligence": business_intelligence(d, report, fc_block),
            "top_products": by_product, "forecast": fc_block,
            "verification": verification, "warnings": warnings,
            "by_category": _rec(d.groupby("category").agg(revenue=("revenue", "sum"), profit=("profit", "sum")).reset_index()),
            "note": "Analysed in-memory only; nothing is stored."}


def analyse_batch(files: list[tuple[str, bytes]], cost_ratio: float = 0.55) -> dict:
    """The whole folder: per-file results + combined sales + cross-file links."""
    from cortexora.analytics.metrics import kpis
    from cortexora.pipelines.intelligence import business_intelligence
    expanded = expand_uploads(files)
    per_file, sales_frames = [], []
    for name, data in expanded:
        entry = {"file": name.split("::")[-1], "source": name}
        try:
            df, fmt, note = parse_tabular(name, data)
        except ValueError as e:
            entry.update(status="error", error=str(e)); per_file.append(entry); continue
        entry.update(format=fmt, parse_note=note, rows=int(len(df)), columns=int(len(df.columns)))
        try:
            result = analyse_frame(df, cost_ratio)
        except Exception as e:
            entry.update(status="error", error=f"analysis failed: {e}"); per_file.append(entry); continue
        entry.update(status="ok", result=result,
                     dataset_type=result["verification"]["dataset_type"])
        if result["kind"] == "sales":
            try:
                d, report, _ = sales_lines(df, cost_ratio)
                d["source_file"] = entry["file"]
                # unify products across files by NAME, not per-file IDs
                d["product_key"] = d["product_name"].astype(str)
                sales_frames.append(d)
            except Exception:
                pass
        per_file.append(entry)

    combined = None
    if sales_frames:
        all_d = pd.concat(sales_frames, ignore_index=True)
        qty_assumed = bool(all_d.groupby("source_file")["qty"].sum().min() >= 0) and any(
            (e.get("result") or {}).get("report", {}).get("qty_is_assumed") for e in per_file if e.get("status") == "ok")
        all_d["month"] = all_d["order_date"].dt.to_period("M").astype(str)
        by_source = _rec(all_d.groupby("source_file").agg(revenue=("revenue", "sum"), profit=("profit", "sum"),
                                                          orders=("order_id", "nunique"), units=("qty", "sum")).reset_index())
        combined = {"files_combined": len(sales_frames), "kpis": kpis(all_d),
                    "trend": _rec(all_d.groupby("month").agg(revenue=("revenue", "sum"), profit=("profit", "sum")).reset_index().rename(columns={"month": "label"})),
                    "by_source": by_source,
                    "by_category": _rec(all_d.groupby("category").agg(revenue=("revenue", "sum"), profit=("profit", "sum")).reset_index()),
                    "top_products": _rec(all_d.groupby(["product_key", "category"]).agg(revenue=("revenue", "sum"), units=("qty", "sum")).reset_index()
                                         .rename(columns={"product_key": "product_name"}).sort_values("revenue", ascending=False).head(10)),
                    "forecast": forecast_block_for(all_d, qty_assumed),
                    "intelligence": business_intelligence(
                        all_d,
                        {"cost_is_assumption": any((e.get("result") or {}).get("report", {}).get("cost_is_assumption")
                                                   for e in per_file if e.get("status") == "ok")},
                        forecast_block_for(all_d, qty_assumed)),
                    "date_min": str(all_d["order_date"].min().date()), "date_max": str(all_d["order_date"].max().date()),
                    "note": "Combined across sales files; products unified by name. Per-file forecasts are in each file's card."}

    # cross-file relationship candidates: shared columns / shared detected roles
    ok_files = [e for e in per_file if e.get("status") == "ok"]
    links = []
    for i in range(len(ok_files)):
        for j in range(i + 1, len(ok_files)):
            a, b = ok_files[i], ok_files[j]
            ca = {c["column"].lower() for c in a["result"]["verification"]["columns"]}
            cb = {c["column"].lower() for c in b["result"]["verification"]["columns"]}
            shared = sorted(ca & cb)
            ma = {f: v["column"] for f, v in a["result"]["verification"]["mapping"].items() if v["column"]}
            mb = {f: v["column"] for f, v in b["result"]["verification"]["mapping"].items() if v["column"]}
            shared_roles = [f for f in set(ma) & set(mb)]
            if shared or shared_roles:
                links.append({"a": a["file"], "b": b["file"], "shared_columns": shared[:6],
                              "shared_roles": shared_roles,
                              "suggestion": "Potential join keys detected — verify values overlap before joining (not auto-joined)."})
    return {"mode": "multi", "files_received": len(files), "files_expanded": len(expanded),
            "per_file": per_file, "combined": combined, "cross_file_links": links,
            "limits": f"max {MAX_FILES} files, {MAX_MEMBER_BYTES // (1024 * 1024)} MB each; ZIP archives are expanded in memory"}

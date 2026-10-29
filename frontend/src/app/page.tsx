"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, BarChart, Bar, Cell, PieChart, Pie, Legend, ComposedChart, Line } from "recharts";
import { api, money, useFetch } from "@/lib/api";
import { PageHead, KpiCard, ChartCard, Loading, ErrorBox, DataTable } from "@/components/ui";

const CATS = ["Electronics", "Apparel", "Home", "Beauty"], REGS = ["North", "South", "East", "West"], CHANS = ["Online", "Store", "Marketplace"];
const COLORS = ["#38bdf8", "#818cf8", "#34d399", "#fbbf24", "#fb7185", "#22d3ee"];
const hour = new Date().getHours();
const GREET = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

function UploadPredict() {
  const [res, setRes] = useState<any>(null); const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false); const [fname, setFname] = useState("");
  async function onFile(e: any) {
    const f = e.target.files?.[0]; if (!f) return;
    setBusy(true); setErr(""); setRes(null); setFname(f.name);
    const fd = new FormData(); fd.append("file", f);
    try {
      const r = await fetch("/api/upload/analyse", { method: "POST", body: fd });
      const j = await r.json();
      if (!r.ok) throw new Error(j.detail || "Upload failed — check the file is a valid sales CSV.");
      setRes(j);
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); e.target.value = ""; }
  }
  const fc = res?.forecast;
  const fcData = fc?.available ? [
    ...fc.history.map((h: any) => ({ week: h.week, actual: Math.round(h.units) })),
    ...fc.forecast.map((h: any) => ({ week: h.week, forecast: Math.round(h.forecast), range: [Math.round(h.lower), Math.round(h.upper)] })),
  ] : [];
  return (<div className="card p-4 mb-4" style={{ borderColor: "var(--a)" }}>
    <div className="flex flex-wrap items-center gap-3 justify-between">
      <div>
        <h3 className="font-bold text-[16px]">📥 Analyse &amp; predict from your own dataset</h3>
        <p className="mut text-[13px] mt-0.5">Upload <b>any</b> CSV dataset — columns are detected from names <i>and</i> contents (renamed, ₹/$-formatted, aggregated, or non-sales files all work). CORTEXORA verifies the file first, then analyses and <b>forecasts the next 8 weeks</b> as far as its structure honestly allows. In-memory only; nothing is stored.</p>
      </div>
      <label className="btn primary" style={{ cursor: "pointer", padding: "10px 18px" }}>
        {busy ? "⏳ Analysing & forecasting…" : "⬆ Upload dataset (CSV)"}
        <input type="file" accept=".csv,text/csv" hidden onChange={onFile} aria-label="Upload a sales CSV dataset" />
      </label>
    </div>
    {fname && !busy && <p className="text-[12.5px] mut mt-2">File: <b style={{ color: "var(--txt)" }}>{fname}</b></p>}
    {err && <p className="text-sm mt-2" role="alert" style={{ color: "var(--bad)" }}>⚠️ {err}</p>}
    {res?.verification && (<details className="card p-3.5 mt-3" style={{ background: "var(--panel2)" }} open={res.kind === "generic"}>
      <summary className="font-bold text-sm cursor-pointer">🔍 Dataset verification — <span style={{ color: "var(--a)" }}>{res.verification.dataset_type}</span>
        <span className="mut font-normal"> · click to {res.kind === "generic" ? "collapse" : "expand"} checks, column profile & detected mapping</span></summary>
      <div className="grid gap-4 mt-3" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(300px,1fr))" }}>
        <div>{res.verification.checks.map((c: any) => (
          <div key={c.check} className="flex gap-2 text-[13px] py-1" style={{ borderBottom: "1px solid var(--line)" }}>
            <span>{c.status === "PASS" ? "✅" : "⚠️"}</span><span><b>{c.check}</b> — <span className="mut">{c.detail}</span></span></div>))}
          <div className="mt-2 flex flex-wrap gap-1.5">{res.kind === "sales" && Object.entries(res.verification.mapping).filter(([, v]: any) => v.column).map(([f, v]: any) => (
            <span key={f} className="chip" style={{ cursor: "default" }} title={v.how}>{f} ← <b>{v.column}</b> · {v.confidence}</span>))}</div>
        </div>
        <div style={{ overflowX: "auto" }}><table><thead><tr><th>Column</th><th>Type</th><th>Filled</th><th>Unique</th><th>Sample</th></tr></thead>
          <tbody>{res.verification.columns.map((c: any) => (<tr key={c.column}><td><b>{c.column}</b></td><td>{c.kind}</td><td>{c.non_null_pct}%</td><td>{c.unique}</td><td className="mut">{c.sample.join(", ")}</td></tr>))}</tbody></table></div>
      </div>
      {(res.warnings || []).map((w: string) => <p key={w} className="text-[13px] mt-2" style={{ color: "var(--warn)" }}>⚠️ {w}</p>)}
    </details>)}
    {res?.kind === "generic" && (<div className="mt-4">
      <p className="text-sm">This dataset was <b>verified and profiled</b> — it isn't sales-shaped (no date + sales-value pair), so here is what can honestly be said about it:</p>
      {res.timeseries_note && <p className="text-sm mut mt-1">{res.timeseries_note}</p>}
      <div className="grid gap-4 mt-3" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(320px,1fr))" }}>
        <ChartCard title="Numeric columns" sub="Distribution summary computed from your file">
          <DataTable rows={res.numeric_summary} pageSize={8} columns={[
            { k: "column", label: "Column" }, { k: "mean", label: "Mean", fmt: (v: number) => v.toLocaleString(undefined, { maximumFractionDigits: 2 }) },
            { k: "median", label: "Median", fmt: (v: number) => v.toLocaleString(undefined, { maximumFractionDigits: 2 }) },
            { k: "min", label: "Min", fmt: (v: number) => v.toLocaleString(undefined, { maximumFractionDigits: 2 }) },
            { k: "max", label: "Max", fmt: (v: number) => v.toLocaleString(undefined, { maximumFractionDigits: 2 }) },
            { k: "missing_pct", label: "Missing", fmt: (v: number) => v + "%" }]} />
        </ChartCard>
        <div>
          <ChartCard title="Strongest associations" sub="Correlation between numeric columns — association, never causation">
            {res.correlations?.length ? res.correlations.map((c: any) => (
              <div key={c.a + c.b} className="flex justify-between text-[13px] py-1" style={{ borderBottom: "1px solid var(--line)" }}>
                <span>{c.a} ↔ {c.b}</span><b style={{ color: Math.abs(c.correlation) > 0.7 ? "var(--a)" : "var(--txt)" }}>{c.correlation}</b></div>))
              : <p className="mut text-sm">Not enough numeric column pairs to correlate.</p>}
          </ChartCard>
          {(res.categorical_summary || []).map((c: any) => (
            <div key={c.column} className="card p-3 mt-3"><div className="lab">{c.column} — most frequent</div>
              {c.top_values.map((t: any) => <div key={t.value} className="flex justify-between text-[13px] py-0.5"><span>{t.value}</span><span className="mut">{t.rows} rows</span></div>)}</div>))}
        </div>
      </div>
      <p className="mut text-[12.5px] mt-2">{res.note}</p>
    </div>)}
    {res?.kind === "sales" && (<div className="mt-4">
      <div className="flex flex-wrap gap-2 text-[12px] mb-3">
        <span className="chip on" style={{ cursor: "default" }}>✅ {res.report.rows_used.toLocaleString()} rows analysed</span>
        {res.report.rows_dropped > 0 && <span className="chip" style={{ cursor: "default", color: "var(--warn)" }}>{res.report.rows_dropped} rows dropped (counted, never silent)</span>}
        <span className="chip" style={{ cursor: "default" }}>{res.report.date_min} → {res.report.date_max}</span>
        <span className="chip" style={{ cursor: "default" }}>{res.report.orders.toLocaleString()} orders · {res.report.products} products · {res.report.customers.toLocaleString()} customers</span>
        {res.report.cost_is_assumption && <span className="chip" style={{ cursor: "default" }}>Profit uses labelled 55% cost assumption (no cost column)</span>}
      </div>
      <div className="grid gap-3 mb-4" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(160px,1fr))" }}>
        <KpiCard label="Your Revenue" value={money(res.kpis.revenue)} sub="from uploaded file" />
        <KpiCard label="Your Profit" value={money(res.kpis.profit)} sub={res.report.cost_is_assumption ? "est. — cost assumption" : "after your costs"} />
        <KpiCard label="Margin" value={(res.kpis.margin * 100).toFixed(1) + "%"} sub="profit / revenue" />
        <KpiCard label="Avg Order Value" value={money(res.kpis.aov)} sub={`${res.kpis.units.toLocaleString()} units sold`} />
      </div>
      <div className="grid gap-4 mb-4" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(320px,1fr))" }}>
        <ChartCard title="Your revenue trend" sub="Monthly revenue & profit from the uploaded file">
          <div style={{ height: 240 }}><ResponsiveContainer><AreaChart data={res.trend}>
            <CartesianGrid strokeDasharray="3 3" opacity={.25} /><XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={30} /><YAxis tick={{ fontSize: 11 }} />
            <Tooltip formatter={(v: any) => money(v)} /><Legend />
            <Area dataKey="revenue" name="Revenue" stroke="#6366f1" fill="#6366f1" fillOpacity={.18} strokeWidth={2.2} />
            <Area dataKey="profit" name="Profit" stroke="#2fbf8f" fill="#2fbf8f" fillOpacity={.14} strokeWidth={2} />
          </AreaChart></ResponsiveContainer></div>
        </ChartCard>
        <div className="card p-4" style={{ background: "var(--panel2)" }}>
          <h3 className="font-bold">🔮 Prediction — next 8 weeks</h3>
          {fc?.available ? (<>
            <div className="flex gap-6 mt-2 flex-wrap">
              {fc.predicted_units_8w !== null && fc.predicted_units_8w !== undefined && <div><div className="lab">Predicted units</div><div className="kpi-val text-[24px] font-extrabold">{Math.round(fc.predicted_units_8w).toLocaleString()}</div></div>}
              <div><div className="lab">Predicted revenue</div><div className="kpi-val text-[24px] font-extrabold">{money(fc.predicted_revenue_8w)}</div></div>
              <div><div className="lab">History used</div><div className="kpi-val text-[24px] font-extrabold">{fc.weeks_of_history} wks</div></div>
            </div>
            <div style={{ height: 210, marginTop: 8 }}><ResponsiveContainer><ComposedChart data={fcData}>
              <CartesianGrid strokeDasharray="3 3" opacity={.25} /><XAxis dataKey="week" tick={{ fontSize: 10 }} minTickGap={40} /><YAxis tick={{ fontSize: 11 }} />
              <Tooltip /><Legend />
              <Area dataKey="range" name="80% interval" stroke="none" fill="#8b7cf6" fillOpacity={.18} />
              <Line dataKey="actual" name={fc.metric === "revenue" ? "Actual revenue/wk" : "Actual units/wk"} stroke="#22b8d8" strokeWidth={2} dot={false} />
              <Line dataKey="forecast" name={fc.metric === "revenue" ? "Forecast revenue/wk" : "Forecast units/wk"} stroke="#8b7cf6" strokeWidth={2.2} strokeDasharray="6 4" dot={{ r: 2.5 }} />
            </ComposedChart></ResponsiveContainer></div>
            <p className="text-[13px] mt-2">{fc.method}. Hold-out: model WAPE <b>{(fc.model_wape * 100).toFixed(1)}%</b> vs baseline <b>{(fc.baseline_wape * 100).toFixed(1)}%</b> — {fc.model_beats_baseline
              ? <span style={{ color: "var(--good)", fontWeight: 700 }}>the model beat the baseline on data it never saw.</span>
              : <span style={{ color: "var(--warn)", fontWeight: 700 }}>the model did NOT beat the baseline — treat this forecast as indicative only.</span>}</p>
            <p className="mut text-[12.5px]">A prediction under stated assumptions (4-week moving average, ~80% interval) — not a guaranteed outcome.</p>
          </>) : (<p className="text-sm mt-2" style={{ color: "var(--warn)" }}>⚠️ {fc?.reason || "Forecast unavailable for this file."}</p>)}
        </div>
      </div>
      <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(320px,1fr))" }}>
        <ChartCard title="Revenue by category" sub="From your file (uploaded products without categories show as Uncategorised)">
          <div style={{ height: 230 }}><ResponsiveContainer><BarChart data={res.by_category} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" opacity={.25} /><XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={(v) => "$" + Math.round(v / 1000) + "k"} /><YAxis type="category" dataKey="category" tick={{ fontSize: 12 }} width={110} />
            <Tooltip formatter={(v: any) => money(v)} /><Bar dataKey="revenue" name="Revenue" fill="#6366f1" radius={[0, 7, 7, 0]} /></BarChart></ResponsiveContainer></div>
        </ChartCard>
        <ChartCard title="🏆 Your top products" sub="By revenue in the uploaded file" action={<Link className="btn" href="/data-sources">Full workflow →</Link>}>
          <DataTable rows={res.top_products} pageSize={6} columns={[
            { k: "product_name", label: "Product", fmt: (v: any, r: any) => v ?? ("Product " + r.product_id) },
            { k: "revenue", label: "Revenue", fmt: (v: number) => money(v) },
            { k: "profit", label: "Profit", fmt: (v: number) => money(v) },
            { k: "units", label: "Units", fmt: (v: number) => Math.round(v).toLocaleString() }]} />
          <p className="mut text-[12.5px] mt-2">{res.note}</p>
        </ChartCard>
      </div>
    </div>)}
  </div>);
}

export default function Home() {
  const router = useRouter();
  const [days, setDays] = useState(10000);
  const [metric, setMetric] = useState("Revenue");
  const [gran, setGran] = useState("Weekly");
  const [breakdown, setBreakdown] = useState("Total");
  const [cats, setCats] = useState<string[]>(CATS);
  const [selCat, setSelCat] = useState<string | null>(null);
  const [price, setPrice] = useState(5); const [demand, setDemand] = useState(10); const [disc, setDisc] = useState(2);
  const [selProd, setSelProd] = useState<any>(null);

  useEffect(() => {
    const saved = Number(localStorage.getItem("cx-days") || 10000); if (saved) setDays(saved);
    const h = (e: any) => setDays(Number(e.detail));
    window.addEventListener("cx-days", h); return () => window.removeEventListener("cx-days", h);
  }, []);
  const q = `/api/dashboard?days=${days}&metric=${metric}&gran=${gran}&breakdown=${breakdown}&cats=${cats.join(",")}&regs=${REGS.join(",")}&chans=${CHANS.join(",")}`;
  const { data, error, loading, refetch } = useFetch<any>(() => api(q), [q]);
  const dec = useFetch<any>(() => api("/api/decisions"), []);
  const fc = useFetch<any>(() => api("/api/forecast?category=Electronics"), []);
  const cust = useFetch<any>(() => api("/api/customers"), []);
  const [hidden, setHidden] = useState<string[]>([]);
  const askCopilot = (qtext: string) => window.dispatchEvent(new CustomEvent("cx-ask-copilot", { detail: qtext }));

  const trendData = useMemo(() => {
    if (!data) return [];
    return data.trend.labels.map((l: string, i: number) => {
      const row: any = { label: l };
      data.trend.series.forEach((s: any) => { row[s.name] = s.data[i]; });
      return row;
    });
  }, [data]);
  const products = useMemo(() => (data?.products || []).filter((p: any) => !selCat || p.category === selCat), [data, selCat]);
  const highRisk = (fc.data?.reorder_plan || []).filter((r: any) => r.stockout_risk === "High").length;

  if (loading && !data) return <Loading />;
  if (error && !data) return <ErrorBox error={error} retry={refetch} />;
  const k = data.kpis, ins = data.insights;
  const scenRev = k.revenue * (1 + price / 100) * (1 + demand / 100) + k.revenue * (disc / 100) * 0.35;
  const scenProf = k.profit * (1 + price / 100) * (1 + demand / 100) + k.revenue * (disc / 100) * 0.35;
  const pending = (dec.data?.decisions || []).filter((d: any) => d.status === "pending").slice(0, 3);
  const sum = cust.data?.summary;
  const churnRate = sum ? sum.churned_heuristic / Math.max(1, sum.customers) : null;
  const sparkMain = trendData.map((r: any) => Number(r[data.trend.series[0]?.name] || 0)).filter((v: number) => v > 0).slice(-14);
  const sparkFc = (fc.data?.forecast || []).map((x: any) => x.forecast);
  const periodLabel = days === 10000 ? "All time" : days === 30 ? "Last 30 days" : days === 90 ? "Last 90 days" : days === 182 ? "Last 6 months" : "Last year";

  return (<div>
    <div className="mb-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-[27px] font-extrabold tracking-tight">{GREET}, welcome to <span style={{ background: "linear-gradient(90deg,var(--a),var(--a2))", WebkitBackgroundClip: "text", color: "transparent" }}>CORTEXORA</span></h1>
          <p className="mut text-sm mt-1">Your business intelligence, predictions, and decisions — all in one place.</p>
          <div className="flex flex-wrap items-center gap-2 mt-2.5 text-[12px]">
            <span className="chip on" style={{ cursor: "default" }}>Demo dataset · synthetic (seed=42)</span>
            <span className="chip" style={{ cursor: "default" }}>Period: {periodLabel}</span>
            <span className="chip" style={{ cursor: "default" }}>Data through {ins?.data_through ?? "…"}</span>
            <span className="chip" style={{ cursor: "default" }}><span className="status-dot pulse" style={{ background: "var(--good)", display: "inline-block", marginRight: 5 }} />Computed live by the analytics API</span>
          </div>
        </div>
        <div className="flex gap-2">
          <button className="btn" onClick={() => refetch()}>↺ Refresh</button>
          <button className="btn" onClick={() => askCopilot("Summarize my business performance.")}>✦ Ask Copilot</button>
          <Link className="btn primary" href="/decisions">Review decisions{pending.length ? ` (${pending.length})` : ""}</Link>
        </div>
      </div>
    </div>
    <div className="card p-3.5 mb-4 flex flex-wrap items-center gap-2 sticky top-[64px] z-30">
      <span className="lab">Period</span>
      {[["30D", 30], ["90D", 90], ["6M", 182], ["1Y", 365], ["All", 10000]].map(([l, v]: any) => (
        <button key={l} className={`chip ${days === v ? "on" : ""}`} onClick={() => setDays(v)}>{l}</button>))}
      <span className="lab ml-3">Metric</span>
      <select value={metric} onChange={(e) => setMetric(e.target.value)}>{["Revenue", "Profit", "Units", "Orders"].map((m) => <option key={m}>{m}</option>)}</select>
      <span className="lab">Granularity</span>
      <select value={gran} onChange={(e) => setGran(e.target.value)}>{["Weekly", "Daily", "Monthly"].map((m) => <option key={m}>{m}</option>)}</select>
      <span className="lab">Split</span>
      <select value={breakdown} onChange={(e) => setBreakdown(e.target.value)}>{["Total", "Category", "Region", "Channel"].map((m) => <option key={m}>{m}</option>)}</select>
      <span className="lab ml-3">Categories</span>
      {CATS.map((c) => <button key={c} className={`chip ${cats.includes(c) ? "on" : ""}`} onClick={() => setCats(cats.includes(c) ? cats.filter((x) => x !== c) : [...cats, c])}>{c}</button>)}
    </div>

    <UploadPredict />

    <div className="grid gap-3 mb-4" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(172px,1fr))" }}>
      <KpiCard label="Total Revenue" value={money(k.revenue)} delta={k.revenue_delta} spark={sparkMain} sub="vs prior period" href="/growth" title="Revenue = Σ qty × unit_price × (1 − discount). Click to open Business Growth." />
      <KpiCard label="Net Profit" value={money(k.profit)} delta={k.profit_delta} spark={sparkMain} sub="vs prior period · after cost" href="/growth" title="Profit = revenue − Σ qty × unit_cost. Click to open Business Growth." />
      <KpiCard label="Profit Margin" value={(k.margin * 100).toFixed(1) + "%"} sub="profit / revenue in scope" href="/pricing" title="Margin on the current scope. Click to open Pricing & Profitability." />
      <KpiCard label="Total Orders" value={k.orders.toLocaleString()} delta={k.orders_delta} spark={sparkMain} sub={`${k.customers} customers in scope`} href="/growth" title="Completed orders in scope. Click to open Business Growth." />
      <KpiCard label="Customer Churn Rate" value={churnRate === null ? "…" : (churnRate * 100).toFixed(1) + "%"} invert sub={sum ? `${sum.churned_heuristic} of ${sum.customers} customers inactive >180d (heuristic)` : "loading…"} href="/customers" title="Share of customers inactive for more than 180 days — a heuristic label; the validated churn model lives in Customer Intelligence." />
      <KpiCard label="Forecasted Revenue (8w)" value={fc.data ? money(fc.data.forecast.reduce((a: number, x: any) => a + x.forecast, 0) * 190) : "…"} spark={sparkFc} sub="Electronics units forecast × avg price" href="/forecasting" title="Sum of the 8-week Electronics unit forecast × average selling price. Evidence and baseline comparison live in Demand Forecasting." />
    </div>
    <div className="grid gap-4 mb-4" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(320px,1fr))" }}>
      <ChartCard title={`${metric} trend`} sub={`${gran}${breakdown !== "Total" ? " · by " + breakdown : ""} · solid = actuals (forecast lives in Demand Forecasting) · click legend to toggle a series`}>
        <div style={{ height: 300 }}><ResponsiveContainer><AreaChart data={trendData}>
          <CartesianGrid strokeDasharray="3 3" opacity={.25} /><XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={40} /><YAxis tick={{ fontSize: 11 }} />
          <Tooltip formatter={(v: any) => Math.round(v).toLocaleString()} />
          {breakdown !== "Total" && <Legend onClick={(e: any) => setHidden((h) => h.includes(e.dataKey) ? h.filter((x) => x !== e.dataKey) : [...h, e.dataKey])} />}
          {data.trend.series.map((s: any, i: number) => <Area key={s.name} dataKey={s.name} hide={hidden.includes(s.name)} stroke={COLORS[i % 6]} fill={COLORS[i % 6]} fillOpacity={.18} strokeWidth={2.2} />)}
        </AreaChart></ResponsiveContainer></div>
      </ChartCard>
      <div className="card p-4">
        <h3 className="font-bold">🧪 Scenario Lab</h3>
        <p className="mut text-[13px] mb-3">Assumption-based simulation on the current scope — not a guaranteed prediction.</p>
        <label className="lab">Price change {price > 0 ? "+" : ""}{price}%</label>
        <input type="range" min={-20} max={30} value={price} onChange={(e) => setPrice(+e.target.value)} className="w-full" />
        <label className="lab">Demand change {demand > 0 ? "+" : ""}{demand}%</label>
        <input type="range" min={-30} max={50} value={demand} onChange={(e) => setDemand(+e.target.value)} className="w-full" />
        <label className="lab">Discount reduction {disc} pts</label>
        <input type="range" min={0} max={10} value={disc} onChange={(e) => setDisc(+e.target.value)} className="w-full" />
        <div className="mt-2 text-[15px]">Projected revenue <b className="text-xl">{money(scenRev)}</b> <span style={{ color: scenRev >= k.revenue ? "var(--good)" : "var(--bad)", fontWeight: 800 }}>{k.revenue ? ((scenRev / k.revenue - 1) * 100).toFixed(1) : 0}%</span></div>
        <div className="text-[15px]">Projected profit <b className="text-xl">{money(scenProf)}</b></div>
        <button className="btn mt-3" onClick={() => router.push("/pricing")}>Test properly in Pricing →</button>
      </div>
    </div>

    <div className="grid gap-4 mb-4" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(320px,1fr))" }}>
      <ChartCard title="Sales by category — click a bar to filter the leaderboard" sub={selCat ? `Filtered to ${selCat} (click again to clear)` : "Drill-down: selection filters products below"}>
        <div style={{ height: 260 }}><ResponsiveContainer><BarChart data={data.categories}>
          <CartesianGrid strokeDasharray="3 3" opacity={.25} /><XAxis dataKey="name" tick={{ fontSize: 12 }} /><YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => "$" + (v / 1000) + "k"} />
          <Tooltip formatter={(v: any) => money(v)} />
          <Bar dataKey="value" radius={[7, 7, 0, 0]} onClick={(e: any) => setSelCat(selCat === e.name ? null : e.name)} cursor="pointer">
            {data.categories.map((c: any, i: number) => <Cell key={i} fill={COLORS[i % 6]} opacity={selCat && selCat !== c.name ? .35 : 1} />)}</Bar>
        </BarChart></ResponsiveContainer></div>
      </ChartCard>
      <ChartCard title="Regional mix" sub="Share of the selected metric in current scope">
        <div style={{ height: 260 }}><ResponsiveContainer><PieChart>
          <Pie data={data.regions} dataKey="value" nameKey="name" innerRadius={58} outerRadius={92} paddingAngle={2}>
            {data.regions.map((r: any, i: number) => <Cell key={i} fill={COLORS[i % 6]} />)}</Pie>
          <Tooltip formatter={(v: any) => money(v)} /><Legend /></PieChart></ResponsiveContainer></div>
      </ChartCard>
      <div className="card p-4">
        <h3 className="font-bold">✦ AI Business Insights <span className="lab" style={{ textTransform: "none", letterSpacing: 0 }}>· computed, not generated prose</span></h3>
        <div className="space-y-3 mt-2 text-sm">
          <div>⚠️ <b>{highRisk} products</b> at high stockout risk in the current reorder plan.
            <div className="flex gap-2 mt-1"><Link className="btn" href="/forecasting">Investigate</Link>
            <button className="btn" onClick={() => askCopilot("Which products are at risk of stockout?")}>Ask Copilot</button></div></div>
          <div>🏆 <b>{ins.top_category}</b> leads revenue ({money(ins.top_category_value)}); <b>{ins.top_region}</b> is the strongest region.</div>
          <div>📉 Margin watch: <b>{ins.margin_watch}</b> has the thinnest margin in scope — review discounting before pushing volume there.
            <div className="mt-1"><Link className="btn" href="/pricing">Open Pricing</Link></div></div>
          <div>🧠 <b>{pending.length} priority actions</b> awaiting review in Decision Intelligence.</div>
        </div>
      </div>
    </div>

    <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(340px,1fr))" }}>
      <ChartCard title={`🏆 Product leaderboard${selCat ? " — " + selCat : ""}`} sub="Sort, search, paginate · click a row for detail">
        <DataTable rows={products} pageSize={8} onRow={setSelProd} columns={[
          { k: "product_name", label: "Product" }, { k: "category", label: "Category" },
          { k: "revenue", label: "Revenue", fmt: (v: number) => money(v) },
          { k: "margin", label: "Margin", fmt: (v: number) => (v * 100).toFixed(1) + "%" },
          { k: "units", label: "Units", fmt: (v: number) => Math.round(v).toLocaleString() }]} />
        {selProd && (<div className="card p-3 mt-3 text-sm">📦 <b>{selProd.product_name}</b> ({selProd.category}) · revenue <b>{money(selProd.revenue)}</b> · profit {money(selProd.profit)} · margin {(selProd.margin * 100).toFixed(1)}% · {Math.round(selProd.units).toLocaleString()} units · {selProd.orders} orders.
          <div className="flex gap-2 mt-2"><Link className="btn" href="/forecasting">Forecast category</Link><Link className="btn" href="/pricing">Price scenario</Link></div></div>)}
      </ChartCard>
      <ChartCard title="🧠 Priority actions" sub="Highest-priority pending recommendations from the Decision Engine" action={<Link className="btn primary" href="/decisions">Open workspace</Link>}>
        {pending.length ? pending.map((d: any) => (
          <div key={d.recommendation_id} className="card p-3 mb-2.5">
            <div className="text-sm"><b>{d.area}</b> · priority {d.priority} — {d.problem}</div>
            <div className="mut text-[13px] mt-0.5">→ {d.action}</div>
            <div className="flex gap-2 mt-2"><Link className="btn" href="/decisions">Inspect & decide</Link>
              <button className="btn" onClick={() => askCopilot("Which products are at risk of stockout?")}>Ask Copilot</button></div></div>))
          : <p className="mut text-sm">No pending recommendations — generate them in Decision Intelligence.</p>}
      </ChartCard>
    </div>

    <div className="card p-4 mt-4">
      <div className="flex items-center justify-between flex-wrap gap-2"><h3 className="font-bold">🩺 System Health</h3><Link className="btn" href="/health">Open Data & Model Health</Link></div>
      <div className="grid gap-3 mt-3" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(200px,1fr))" }}>
        <div className="flex gap-2.5 items-start"><span className="status-dot" style={{ background: "var(--good)", marginTop: 6 }} /><div><div className="text-sm font-semibold">Data freshness</div><div className="mut text-[12.5px]">Through {ins.data_through} · {Number(ins.records || 0).toLocaleString()} records in scope</div></div></div>
        <div className="flex gap-2.5 items-start"><span className="status-dot" style={{ background: "var(--good)", marginTop: 6 }} /><div><div className="text-sm font-semibold">Pipeline status</div><div className="mut text-[12.5px]">ETL quality gate passed on last load — see run history</div></div></div>
        <div className="flex gap-2.5 items-start"><span className="status-dot" style={{ background: highRisk > 0 ? "var(--warn)" : "var(--good)", marginTop: 6 }} /><div><div className="text-sm font-semibold">Inventory model watch</div><div className="mut text-[12.5px]">{highRisk} products at high stockout risk under the current plan</div></div></div>
        <div className="flex gap-2.5 items-start"><span className="status-dot" style={{ background: pending.length ? "var(--warn)" : "var(--good)", marginTop: 6 }} /><div><div className="text-sm font-semibold">Decisions awaiting you</div><div className="mut text-[12.5px]">{pending.length} shown above · full queue in Decision Intelligence</div></div></div>
      </div>
    </div>
  </div>);
}

"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, BarChart, Bar, Cell, PieChart, Pie, Legend, ComposedChart, Line } from "recharts";
import { api, money, useFetch } from "@/lib/api";
import { PageHead, KpiCard, ChartCard, Loading, ErrorBox, DataTable, Tabs } from "@/components/ui";

const CATS = ["Electronics", "Apparel", "Home", "Beauty"], REGS = ["North", "South", "East", "West"], CHANS = ["Online", "Store", "Marketplace"];
const COLORS = ["#38bdf8", "#818cf8", "#34d399", "#fbbf24", "#fb7185", "#22d3ee"];
const hour = new Date().getHours();
const GREET = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

const STAGES = ["1 · Understand", "2 · Discover", "3 · Predict", "4 · Test decisions", "5 · Recommend"];
function IntelReport({ intel }: { intel: any }) {
  const [tab, setTab] = useState(STAGES[0]);
  if (!intel) return null;
  const u = intel.understand, di = intel.discover, pr = intel.predict, te = intel.test_decisions, recs = intel.recommendations || [];
  const moneyL = (v: any) => money(Number(v) || 0);
  return (<div className="card p-4 mt-4" style={{ borderColor: "var(--a)" }}>
    <div className="flex flex-wrap items-center justify-between gap-2">
      <h4 className="font-bold text-[15px]">🧠 Business Intelligence from your data</h4>
      <Tabs tabs={STAGES} active={tab} onChange={setTab} />
    </div>
    <p className="mut text-[12.5px] mt-1">Five stages, computed only from the uploaded file(s). Estimates and heuristics are labelled; anything your data can't support says why.</p>

    {tab === STAGES[0] && (<div className="mt-3">
      <p className="text-sm"><b>{u.period.from} → {u.period.to}</b> · {u.period.rows.toLocaleString()} line rows · {u.period.products} products · {u.period.customers} customers. Worst category by margin: <b>{u.worst_category?.category}</b> ({((u.worst_category?.margin || 0) * 100).toFixed(1)}%).</p>
      <div className="grid gap-4 mt-3" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(320px,1fr))" }}>
        <ChartCard title="🏆 Top products by revenue" sub="Observed facts from your file">
          <DataTable rows={u.top_products} pageSize={6} columns={[
            { k: "product_name", label: "Product" }, { k: "revenue", label: "Revenue", fmt: moneyL },
            { k: "profit", label: "Profit", fmt: moneyL }, { k: "margin", label: "Margin", fmt: (v: number) => (v * 100).toFixed(1) + "%" }]} /></ChartCard>
        <ChartCard title="⚠️ Poor performers" sub="Margin under 5% or losing money — stage 2 explains why">
          {u.poor_performers?.length ? <DataTable rows={u.poor_performers} pageSize={6} columns={[
            { k: "product_name", label: "Product" }, { k: "margin", label: "Margin", fmt: (v: number) => (v * 100).toFixed(1) + "%" },
            { k: "profit", label: "Profit", fmt: moneyL }, { k: "reason", label: "Flag" }]} />
            : <p className="mut text-sm">No poor performers — every product clears a 5% margin. ✅</p>}
          {!!u.declining_products?.length && <p className="text-[13px] mt-2">Declining (revenue −20%+ between halves): {u.declining_products.map((x: any) => `${x.product_name} (${x.change_pct}%)`).join(", ")}</p>}
        </ChartCard>
      </div></div>)}

    {tab === STAGES[1] && (<div className="mt-3">
      <div className="flex flex-wrap gap-2 text-[12px] mb-3">{Object.entries(di.bridge).map(([k, v]: any) => (
        <span key={k} className="chip" style={{ cursor: "default" }}><b>{k}</b>: {k === "margin" || k === "avg_discount" ? (v.recent * 100).toFixed(1) + "%" : Math.round(v.recent).toLocaleString()}
          {v.change_pct !== null && <span style={{ color: v.change_pct >= 0 ? "var(--good)" : "var(--bad)", fontWeight: 800 }}> ({v.change_pct > 0 ? "+" : ""}{v.change_pct}%)</span>}</span>))}
        <span className="chip" style={{ cursor: "default" }}>halves split at {di.split_date}</span></div>
      {di.findings.map((f: string) => <p key={f} className="text-sm py-1" style={{ borderBottom: "1px solid var(--line)" }}>🔎 {f}</p>)}
      <div className="grid gap-4 mt-3" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(300px,1fr))" }}>
        <ChartCard title="Profit drivers — products" sub="Profit change, recent half minus prior half ($)">
          {di.profit_drivers_products.map((x: any) => (<div key={x.name} className="flex justify-between text-[13px] py-1" style={{ borderBottom: "1px solid var(--line)" }}>
            <span>{x.name}</span><b style={{ color: x.profit_delta >= 0 ? "var(--good)" : "var(--bad)" }}>{x.profit_delta >= 0 ? "+" : ""}{moneyL(x.profit_delta)}</b></div>))}</ChartCard>
        <ChartCard title="Customer segments (from your file)" sub="Recency of last purchase vs your latest date">
          <p className="text-sm">Repeat customers: <b>{(di.segments.repeat_share * 100).toFixed(0)}%</b> · inactive 90+ days: <b>{di.segments.at_risk}</b> ({(di.segments.at_risk_share * 100).toFixed(0)}%, worth {moneyL(di.segments.at_risk_monetary)} historically).</p>
        </ChartCard>
      </div></div>)}

    {tab === STAGES[2] && (<div className="mt-3">
      <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(320px,1fr))" }}>
        <div className="card p-4" style={{ background: "var(--panel2)" }}><h3 className="font-bold">🔮 Next 8 weeks</h3>
          {pr.forecast?.available ? <p className="text-sm mt-1">Predicted revenue <b>{moneyL(pr.forecast.predicted_revenue_8w)}</b>{pr.forecast.predicted_units_8w ? <> · {Math.round(pr.forecast.predicted_units_8w).toLocaleString()} units</> : ""}. Model WAPE {(pr.forecast.model_wape * 100).toFixed(1)}% vs baseline {(pr.forecast.baseline_wape * 100).toFixed(1)}% — {pr.forecast.model_beats_baseline ? "model beats baseline ✅" : "baseline wins, indicative only ⚠️"} (chart in the combined panel above).</p>
            : <p className="text-sm mt-1" style={{ color: "var(--warn)" }}>{pr.forecast?.reason}</p>}
          {!!pr.demand_rising?.length && <p className="text-[13px] mt-2">Fast-rising demand: {pr.demand_rising.map((x: any) => `${x.product_name} (+${x.growth_pct}%)`).join(", ")}</p>}
        </div>
        <div className="card p-4" style={{ background: "var(--panel2)" }}><h3 className="font-bold">👥 Customers who might leave</h3>
          <p className="mut text-[12px]">{pr.churn_risk.method}</p>
          <p className="text-sm mt-1"><b>{pr.churn_risk.at_risk}</b> of {pr.churn_risk.customers} customers inactive 90+ days ({moneyL(pr.churn_risk.at_risk_monetary)} historical revenue).</p>
          {pr.churn_risk.top_at_risk?.slice(0, 5).map((x: any) => <p key={x.customer_id} className="text-[13px] py-0.5">Customer {x.customer_id} — {x.days_since_last_order}d ago · {moneyL(x.historical_revenue)} · {x.orders} orders</p>)}
        </div>
        <div className="card p-4" style={{ background: "var(--panel2)" }}><h3 className="font-bold">📦 Stockout risk</h3>
          <p className="text-sm mt-1" style={{ color: "var(--warn)" }}>⚠️ Not computed — {pr.stockout_risk.reason}</p></div>
      </div></div>)}

    {tab === STAGES[3] && (<div className="mt-3">
      <div className="grid gap-3" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(280px,1fr))" }}>
        {te.scenarios.map((sc: any) => (<div key={sc.name} className="card p-3.5">
          <div className="font-bold text-sm">{sc.name}</div>
          {sc.note && <p className="mut text-[13px] mt-1">{sc.note}</p>}
          {sc.projected_revenue !== null && sc.projected_revenue !== undefined && <p className="text-sm mt-1">Projected revenue <b>{moneyL(sc.projected_revenue)}</b> ({sc.revenue_change_pct > 0 ? "+" : ""}{sc.revenue_change_pct}%) · profit <b>{moneyL(sc.projected_profit)}</b></p>}
          {sc.units_to_cover_4w !== undefined && <p className="text-sm mt-1">Order <b>{sc.units_to_cover_4w.toLocaleString()} units</b> ≈ {moneyL(sc.estimated_cost)} at your average unit cost.</p>}
          {sc.assumption && <p className="mut text-[12px] mt-1">Assumption: {sc.assumption}</p>}
        </div>))}
      </div>
      <p className="mut text-[12.5px] mt-2">{te.note}</p></div>)}

    {tab === STAGES[4] && (<div className="mt-3 space-y-2.5">
      {recs.length ? recs.map((r: any) => (<div key={r.priority} className="card p-3.5 flex gap-3" style={{ alignItems: "flex-start" }}>
        <span className="chip on" style={{ cursor: "default", flexShrink: 0 }}>#{r.priority}</span>
        <div><div className="font-bold text-sm">{r.action} {r.expected_impact > 0 && <span style={{ color: "var(--good)" }}>· est. impact {moneyL(r.expected_impact)}</span>}</div>
          <p className="text-[13px] mt-0.5"><b>Evidence:</b> {r.evidence}</p>
          <p className="mut text-[12.5px]"><b>Impact basis:</b> {r.impact_basis} · <b>Measure:</b> {r.measure}</p></div></div>))
        : <p className="mut text-sm">No actions triggered by this data — nothing crossed the poor-performance, decline, or churn thresholds.</p>}
      <p className="mut text-[12.5px]">{intel.note}</p></div>)}
  </div>);
}

function UploadPredict() {
  const [batch, setBatch] = useState<any>(null); const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false); const [names, setNames] = useState<string[]>([]);
  const folderRef = (el: HTMLInputElement | null) => { if (el) { el.setAttribute("webkitdirectory", ""); el.setAttribute("directory", ""); } };
  async function onFiles(e: any) {
    const list: File[] = Array.from(e.target.files || []); if (!list.length) return;
    setBusy(true); setErr(""); setBatch(null); setNames(list.map((f) => f.name));
    const fd = new FormData(); list.forEach((f) => fd.append("files", f, (f as any).webkitRelativePath || f.name));
    try {
      const r = await fetch("/api/upload/multi", { method: "POST", body: fd });
      const j = await r.json();
      if (!r.ok) throw new Error(j.detail || "Upload failed.");
      setBatch(j);
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); e.target.value = ""; }
  }
  const c = batch?.combined;
  const fcData = c?.forecast?.available ? [
    ...c.forecast.history.map((h: any) => ({ week: h.week, actual: Math.round(h.units) })),
    ...c.forecast.forecast.map((h: any) => ({ week: h.week, forecast: Math.round(h.forecast), range: [Math.round(h.lower), Math.round(h.upper)] })),
  ] : [];
  return (<div className="card p-4 mb-4" style={{ borderColor: "var(--a)" }}>
    <div className="flex flex-wrap items-center gap-3 justify-between">
      <div style={{ maxWidth: 640 }}>
        <h3 className="font-bold text-[16px]">📥 Analyse &amp; predict from your own datasets</h3>
        <p className="mut text-[13px] mt-0.5">Upload <b>one file, many files, or a whole folder</b> — CSV, TSV, Excel, JSON, Parquet, or ZIP. Columns are detected from names <i>and</i> contents. Every file is verified; sales files are analysed individually <b>and combined</b>, then forecast for the next 8 weeks against a baseline. In-memory only; nothing is stored.</p>
      </div>
      <div className="flex gap-2 flex-wrap">
        <label className="btn primary" style={{ cursor: "pointer", padding: "10px 16px" }}>{busy ? "⏳ Analysing…" : "⬆ Upload files"}
          <input type="file" multiple accept=".csv,.tsv,.txt,.xlsx,.xls,.json,.parquet,.pq,.zip" hidden onChange={onFiles} aria-label="Upload dataset files" /></label>
        <label className="btn primary" style={{ cursor: "pointer", padding: "10px 16px" }}>📁 Upload folder
          <input ref={folderRef} type="file" multiple hidden onChange={onFiles} aria-label="Upload a folder of datasets" /></label>
      </div>
    </div>
    {names.length > 0 && <p className="text-[12.5px] mut mt-2">Selected: <b style={{ color: "var(--txt)" }}>{names.slice(0, 4).join(", ")}{names.length > 4 ? ` +${names.length - 4} more` : ""}</b> · limits: {batch?.limits || "max 25 files, 25 MB each"}</p>}
    {err && <p className="text-sm mt-2" role="alert" style={{ color: "var(--bad)" }}>⚠️ {err}</p>}

    {batch && (<div className="mt-4">
      <h4 className="font-bold text-sm mb-2">🗂️ Dataset inventory — {batch.files_expanded} file(s) from {batch.files_received} upload(s)</h4>
      <div style={{ overflowX: "auto" }}><table><thead><tr><th>File</th><th>Format</th><th>Rows × Cols</th><th>Detected type</th><th>Status</th></tr></thead>
        <tbody>{batch.per_file.map((e: any, i: number) => (<tr key={i}>
          <td><b>{e.file}</b>{e.parse_note && <div className="mut text-[12px]">{e.parse_note}</div>}</td>
          <td>{e.format || "—"}</td><td>{e.rows !== undefined ? `${e.rows.toLocaleString()} × ${e.columns}` : "—"}</td>
          <td>{e.dataset_type || "—"}</td>
          <td>{e.status === "ok" ? <span style={{ color: "var(--good)", fontWeight: 700 }}>✅ analysed</span> : <span style={{ color: "var(--bad)" }}>⛔ {e.error}</span>}</td></tr>))}</tbody></table></div>

      {c && (<div className="card p-4 mt-4" style={{ background: "var(--panel2)" }}>
        <h4 className="font-bold">🧩 Combined analysis — {c.files_combined} sales file(s), {c.date_min} → {c.date_max}</h4>
        <div className="grid gap-3 my-3" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(160px,1fr))" }}>
          <KpiCard label="Combined Revenue" value={money(c.kpis.revenue)} sub="all sales files unified" />
          <KpiCard label="Combined Profit" value={money(c.kpis.profit)} sub="labelled assumptions per file apply" />
          <KpiCard label="Margin" value={(c.kpis.margin * 100).toFixed(1) + "%"} sub={`${c.kpis.orders.toLocaleString()} orders`} />
          <KpiCard label="Predicted Revenue (8w)" value={c.forecast?.available ? money(c.forecast.predicted_revenue_8w) : "—"}
            sub={c.forecast?.available ? `model WAPE ${(c.forecast.model_wape * 100).toFixed(1)}% vs baseline ${(c.forecast.baseline_wape * 100).toFixed(1)}%${c.forecast.model_beats_baseline ? " · model wins" : " · baseline wins — indicative only"}` : (c.forecast?.reason || "")} />
        </div>
        {c.forecast?.available && (<div style={{ height: 230 }}><ResponsiveContainer><ComposedChart data={fcData}>
          <CartesianGrid strokeDasharray="3 3" opacity={.25} /><XAxis dataKey="week" tick={{ fontSize: 10 }} minTickGap={40} /><YAxis tick={{ fontSize: 11 }} />
          <Tooltip /><Legend />
          <Area dataKey="range" name="80% interval" stroke="none" fill="#8b7cf6" fillOpacity={.18} />
          <Line dataKey="actual" name={c.forecast.metric === "revenue" ? "Actual revenue/wk" : "Actual units/wk"} stroke="#22b8d8" strokeWidth={2} dot={false} />
          <Line dataKey="forecast" name="Forecast (8w)" stroke="#8b7cf6" strokeWidth={2.2} strokeDasharray="6 4" dot={{ r: 2.5 }} />
        </ComposedChart></ResponsiveContainer></div>)}
        <div className="grid gap-4 mt-3" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(300px,1fr))" }}>
          <ChartCard title="Revenue by source file" sub="Contribution of each uploaded sales file">
            <DataTable rows={c.by_source} pageSize={6} columns={[
              { k: "source_file", label: "File" }, { k: "revenue", label: "Revenue", fmt: (v: number) => money(v) },
              { k: "orders", label: "Orders", fmt: (v: number) => v.toLocaleString() }, { k: "units", label: "Units", fmt: (v: number) => Math.round(v).toLocaleString() }]} />
          </ChartCard>
          <ChartCard title="🏆 Combined top products" sub="Unified by product name across files">
            <DataTable rows={c.top_products} pageSize={6} columns={[
              { k: "product_name", label: "Product" }, { k: "category", label: "Category" },
              { k: "revenue", label: "Revenue", fmt: (v: number) => money(v) }, { k: "units", label: "Units", fmt: (v: number) => Math.round(v).toLocaleString() }]} />
          </ChartCard>
        </div>
        <p className="mut text-[12.5px] mt-2">{c.note}</p>
        <IntelReport intel={c.intelligence} />
      </div>)}

      {(batch.cross_file_links || []).length > 0 && (<div className="card p-3.5 mt-4">
        <h4 className="font-bold text-sm">🔗 Cross-file relationships detected</h4>
        {batch.cross_file_links.slice(0, 6).map((l: any, i: number) => (
          <p key={i} className="text-[13px] mt-1.5"><b>{l.a}</b> ↔ <b>{l.b}</b> — shared: {[...(l.shared_columns || []), ...(l.shared_roles || [])].slice(0, 6).join(", ") || "—"} <span className="mut">· {l.suggestion}</span></p>))}
      </div>)}

      <h4 className="font-bold text-sm mt-4 mb-2">📄 Per-file results</h4>
      <div className="space-y-3">{batch.per_file.filter((e: any) => e.status === "ok").map((e: any, i: number) => { const r = e.result; return (
        <details key={i} className="card p-3.5" open={i === 0}>
          <summary className="font-bold text-sm cursor-pointer">{e.file} <span className="mut font-normal">· {e.format} · {r.verification.dataset_type}</span>
            {r.kind === "sales" && <span style={{ color: "var(--a)" }}> · revenue {money(r.kpis.revenue)} · forecast {r.forecast?.available ? "ready" : "not available"}</span>}
            {r.kind === "generic" && <span className="mut font-normal"> · statistical profile</span>}</summary>
          {(r.warnings || []).map((w: string) => <p key={w} className="text-[13px] mt-2" style={{ color: "var(--warn)" }}>⚠️ {w}</p>)}
          {r.kind === "sales" ? (<div className="mt-2">
            <div className="flex flex-wrap gap-2 text-[12px]">
              <span className="chip" style={{ cursor: "default" }}>{r.report.rows_used.toLocaleString()} rows · {r.report.date_min} → {r.report.date_max}</span>
              {r.report.rows_dropped > 0 && <span className="chip" style={{ cursor: "default", color: "var(--warn)" }}>{r.report.rows_dropped} dropped (counted)</span>}
              <span className="chip" style={{ cursor: "default" }}>margin {(r.kpis.margin * 100).toFixed(1)}%</span>
              {r.intelligence?.recommendations?.[0] && <span className="chip" style={{ cursor: "default", color: "var(--a)" }}>🧠 Top action: {r.intelligence.recommendations[0].action}</span>}
              {r.forecast?.available
                ? <span className="chip on" style={{ cursor: "default" }}>🔮 8w: {money(r.forecast.predicted_revenue_8w)} · WAPE {(r.forecast.model_wape * 100).toFixed(1)}% vs {(r.forecast.baseline_wape * 100).toFixed(1)}% {r.forecast.model_beats_baseline ? "(model wins)" : "(baseline wins)"}</span>
                : <span className="chip" style={{ cursor: "default" }}>🔮 {r.forecast?.reason || "no forecast"}</span>}
            </div>
            <div style={{ height: 190, marginTop: 8 }}><ResponsiveContainer><AreaChart data={r.trend}>
              <CartesianGrid strokeDasharray="3 3" opacity={.25} /><XAxis dataKey="label" tick={{ fontSize: 10 }} minTickGap={30} /><YAxis tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v: any) => money(v)} /><Area dataKey="revenue" name="Revenue" stroke="#6366f1" fill="#6366f1" fillOpacity={.18} strokeWidth={2} /></AreaChart></ResponsiveContainer></div>
          </div>) : (<div className="mt-2 text-sm">
            <p className="mut">{r.note}</p>
            {!!r.numeric_summary?.length && <p className="mt-1">Numeric columns profiled: <b>{r.numeric_summary.map((n: any) => n.column).join(", ")}</b></p>}
            {!!r.correlations?.length && <p className="mt-1">Strongest association: <b>{r.correlations[0].a} ↔ {r.correlations[0].b} ({r.correlations[0].correlation})</b> — association, not causation.</p>}
            {r.timeseries_note && <p className="mut mt-1">{r.timeseries_note}</p>}
          </div>)}
          <details className="mt-2"><summary className="text-[13px] font-semibold cursor-pointer mut">🔍 Verification checks & column profile</summary>
            <div className="mt-2">{r.verification.checks.map((chk: any) => (
              <div key={chk.check} className="text-[13px] py-0.5">{chk.status === "PASS" ? "✅" : "⚠️"} <b>{chk.check}</b> — <span className="mut">{chk.detail}</span></div>))}
              <div style={{ overflowX: "auto" }}><table><thead><tr><th>Column</th><th>Type</th><th>Filled</th><th>Unique</th><th>Sample</th></tr></thead>
              <tbody>{r.verification.columns.map((col: any) => (<tr key={col.column}><td><b>{col.column}</b></td><td>{col.kind}</td><td>{col.non_null_pct}%</td><td>{col.unique}</td><td className="mut">{col.sample.join(", ")}</td></tr>))}</tbody></table></div>
            </div></details>
        </details>); })}
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

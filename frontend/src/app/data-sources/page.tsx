"use client";
import { useState } from "react";
import Link from "next/link";
import { api, money, useFetch } from "@/lib/api";
import { PageHead, KpiCard, ChartCard, Loading, ErrorBox, DataTable } from "@/components/ui";
export default function DataSources() {
  const { data, error, loading, refetch } = useFetch<any>(() => api("/api/datasources"), []);
  const [res, setRes] = useState<any>(null); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  if (loading) return <Loading />; if (error) return <ErrorBox error={error} retry={refetch} />;
  async function upload(e: any) {
    const f = e.target.files?.[0]; if (!f) return;
    setBusy(true); setErr(""); setRes(null);
    const fd = new FormData(); fd.append("files", f);
    try {
      const r = await fetch("/api/upload/multi", { method: "POST", body: fd });
      const j = await r.json();
      if (!r.ok) throw new Error(j.detail || "Upload failed");
      setRes(j);
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  }
  return (<div>
    <PageHead title="Data Sources" question="Your data, analysed" desc="Connected warehouse tables, schemas — and a working CSV upload that validates, transforms and analyses your file. Uploaded code is never executed; CSV parsing only." />
    <div className="grid gap-3 mb-4" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(170px,1fr))" }}>
      <KpiCard label="Warehouse" value="SQLite" sub={String(data.warehouse).split("/").slice(-2).join("/")} />
      <KpiCard label="Tables" value={data.sources.length} sub="documented grains (docs/03)" />
      <KpiCard label="Total rows" value={data.sources.reduce((a: number, s: any) => a + s.rows, 0).toLocaleString()} sub="across all tables" />
      <KpiCard label="Active dataset" value={data.mode === "uploaded" ? "📂 Your data" : "Demo Data"} sub={data.mode === "uploaded" ? "every page computes on it" : "synthetic — upload yours below"} /></div>
    <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(330px,1fr))" }}>
      <ChartCard title="Connected tables & schemas" sub="Row counts are live from the warehouse">
        <DataTable rows={data.sources} pageSize={8} columns={[{ k: "table", label: "Table" }, { k: "rows", label: "Rows", fmt: (v: number) => v.toLocaleString() },
          { k: "columns", label: "Columns", fmt: (v: any) => Array.isArray(v) ? v.join(", ") : v }]} /></ChartCard>
      <div className="card p-4"><h3 className="font-bold">📥 Upload & analyse a sales CSV</h3>
        <p className="mut text-[13px]">One row per sold item works best. Columns are auto-detected (InvoiceNo, Quantity, Price, Description…), required: date, product, quantity, unit price. Bad rows are dropped <b>and counted</b>; without a cost column, profit uses a labelled 55% cost assumption.</p>
        <label className="btn primary mt-2" style={{ cursor: "pointer" }}>{busy ? "Analysing…" : "Choose CSV file"}<input type="file" accept=".csv" hidden onChange={upload} /></label>
        {err && <p className="text-sm mt-2" style={{ color: "var(--bad)" }}>⚠️ {err}</p>}
        {res?.activation_error && <p className="text-sm mt-2" style={{ color: "var(--warn)" }}>⚠️ {res.activation_error}</p>}
        {res && (<div className="mt-3 text-sm space-y-1.5">
          {res.combined ? <div>✅ Analysed &amp; combined {res.combined.files_combined} sales file(s) — revenue <b>{money(res.combined.kpis.revenue)}</b>. {res.activated ? <b style={{ color: "var(--good)" }}>This dataset is now LIVE on every page.</b> : "See Home for the full 5-stage report."}</div>
          : <div>✅ Analysed <b>{res.report.rows_used.toLocaleString()}</b> rows ({res.report.orders.toLocaleString()} orders · {res.report.products} products · {res.report.customers.toLocaleString()} customers), {res.report.date_min} → {res.report.date_max}.</div>}
          {!res.combined && res.report?.rows_dropped > 0 && <div style={{ color: "var(--warn)" }}>{res.report.rows_dropped} rows dropped (unparseable) — counted, never silent.</div>}
          {res.combined && <DataTable rows={res.combined.by_category} pageSize={6} columns={[{ k: "category", label: "Category" }, { k: "revenue", label: "Revenue", fmt: (v: number) => money(v) }, { k: "profit", label: "Profit", fmt: (v: number) => money(v) }]} />}
          <p className="mut">{res.note || "Full 5-stage intelligence report is on the Home page."}</p></div>)}
        <p className="mut text-[13px] mt-3">Sales files uploaded here (or on Home) are <b>activated automatically</b>: the warehouse is replaced through the ETL quality gate (decision history preserved) and every page recomputes on your data.</p></div>
      <div className="card p-4"><h3 className="font-bold">🗂️ Active dataset</h3>
        <p className="text-sm mt-1">Currently live: <b>{data.mode === "uploaded" ? "📂 Your uploaded dataset" : "🗂️ Demo dataset (synthetic, seed=42)"}</b></p>
        <p className="mut text-[13px]">Warehouse tables above update the moment a dataset is activated. Decision audit history survives every switch.</p>
        <button className="btn mt-3" onClick={async () => { await fetch("/api/dataset/reset", { method: "POST" }); refetch(); }}>↺ Reset to demo dataset</button>
        <Link className="btn primary ml-2 mt-3" href="/">Upload on Home →</Link></div>
    </div></div>);
}

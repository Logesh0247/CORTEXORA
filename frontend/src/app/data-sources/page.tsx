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
    const fd = new FormData(); fd.append("file", f);
    try {
      const r = await fetch("/api/upload/analyse", { method: "POST", body: fd });
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
      <KpiCard label="Mode" value="Demo Data" sub="synthetic — upload yours below" /></div>
    <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(330px,1fr))" }}>
      <ChartCard title="Connected tables & schemas" sub="Row counts are live from the warehouse">
        <DataTable rows={data.sources} pageSize={8} columns={[{ k: "table", label: "Table" }, { k: "rows", label: "Rows", fmt: (v: number) => v.toLocaleString() },
          { k: "columns", label: "Columns", fmt: (v: any) => Array.isArray(v) ? v.join(", ") : v }]} /></ChartCard>
      <div className="card p-4"><h3 className="font-bold">📥 Upload & analyse a sales CSV</h3>
        <p className="mut text-[13px]">One row per sold item works best. Columns are auto-detected (InvoiceNo, Quantity, Price, Description…), required: date, product, quantity, unit price. Bad rows are dropped <b>and counted</b>; without a cost column, profit uses a labelled 55% cost assumption.</p>
        <label className="btn primary mt-2" style={{ cursor: "pointer" }}>{busy ? "Analysing…" : "Choose CSV file"}<input type="file" accept=".csv" hidden onChange={upload} /></label>
        {err && <p className="text-sm mt-2" style={{ color: "var(--bad)" }}>⚠️ {err}</p>}
        {res && (<div className="mt-3 text-sm space-y-1.5">
          <div>✅ Analysed <b>{res.report.rows_used.toLocaleString()}</b> rows ({res.report.orders.toLocaleString()} orders · {res.report.products} products · {res.report.customers.toLocaleString()} customers), {res.report.date_min} → {res.report.date_max}.</div>
          {res.report.rows_dropped > 0 && <div style={{ color: "var(--warn)" }}>{res.report.rows_dropped} rows dropped (unparseable) — counted, never silent.</div>}
          <div>Revenue <b>{money(res.kpis.revenue)}</b> · Profit <b>{money(res.kpis.profit)}</b>{res.report.cost_is_assumption ? " (est. — cost assumption)" : ""} · Margin {(res.kpis.margin * 100).toFixed(1)}%</div>
          <DataTable rows={res.by_category} pageSize={6} columns={[{ k: "category", label: "Category" }, { k: "revenue", label: "Revenue", fmt: (v: number) => money(v) }, { k: "profit", label: "Profit", fmt: (v: number) => money(v) }]} />
          <p className="mut">{res.note}</p></div>)}
        <p className="mut text-[13px] mt-3">Full workflow (mapping confirmation, forecast, warehouse load): <Link className="underline" href="/health">health checks</Link> run on load; the Streamlit Upload & Analyse page performs the ETL-gated warehouse replacement.</p></div>
    </div></div>);
}

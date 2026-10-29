"use client";
import { useState } from "react";
import { PageHead, KpiCard, ChartCard, DataTable, Empty } from "@/components/ui";
const TEMPLATE = "product_id,competitor,competitor_price,observed_at,source_url\n";
export default function MarketRadar() {
  const [rows, setRows] = useState<any[]>([]); const [err, setErr] = useState("");
  function onFile(e: any) {
    const f = e.target.files?.[0]; if (!f) return;
    f.text().then((txt: string) => {
      try {
        const [head, ...lines] = txt.trim().split("\n");
        const cols = head.split(",").map((c: string) => c.trim());
        const need = ["product_id", "competitor", "competitor_price", "observed_at", "source_url"];
        const missing = need.filter((c) => !cols.includes(c));
        if (missing.length) throw new Error("Missing columns: " + missing.join(", "));
        setRows(lines.filter(Boolean).map((l: string) => { const v = l.split(","); const o: any = {}; cols.forEach((c: string, i: number) => o[c] = v[i]); o.competitor_price = Number(o.competitor_price); return o; }));
        setErr("");
      } catch (e: any) { setErr(e.message); setRows([]); }
    });
  }
  const alerts = rows.filter((r) => r.competitor_price > 0);
  return (<div>
    <PageHead title="Market Radar" question="External signals" desc="Competitor observations YOU supply (compliantly collected, with source + timestamp). No live feed is connected and none is simulated." />
    <div className="card p-4 mb-4" style={{ borderColor: "var(--warn)" }}>
      <b style={{ color: "var(--warn)" }}>⚠️ No continuous monitoring is configured.</b>
      <span className="mut text-sm"> Upload a snapshot CSV to compare competitor prices against the catalogue. Required columns: product_id, competitor, competitor_price, observed_at, source_url.</span>
      <div className="flex gap-2 mt-3 flex-wrap">
        <a className="btn" href={`data:text/csv;charset=utf-8,${encodeURIComponent(TEMPLATE + "1,RivalCo,99.00,2026-10-01,https://example.com/p1")}`} download="competitor_template.csv">⬇ Download template</a>
        <label className="btn" style={{ cursor: "pointer" }}>📥 Upload snapshot CSV<input type="file" accept=".csv" hidden onChange={onFile} /></label></div>
      {err && <p className="text-sm mt-2" style={{ color: "var(--bad)" }}>Invalid snapshot: {err}</p>}</div>
    <div className="grid gap-3 mb-4" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))" }}>
      <KpiCard label="Observations loaded" value={rows.length} sub="from your upload" />
      <KpiCard label="Competitors" value={new Set(rows.map((r) => r.competitor)).size} sub="distinct sources in file" />
      <KpiCard label="Latest observation" value={rows.length ? rows.map((r) => r.observed_at).sort().slice(-1)[0] : "—"} sub="as supplied by you" /></div>
    <ChartCard title="Snapshot comparison" sub="Gap analysis vs our list price is computed in the full app (Competitor Intelligence) once product IDs are validated against the catalogue">
      {rows.length ? <DataTable rows={rows} pageSize={10} columns={[{ k: "product_id", label: "Product" }, { k: "competitor", label: "Competitor" },
        { k: "competitor_price", label: "Their price", fmt: (v: number) => "$" + v.toFixed(2) }, { k: "observed_at", label: "Observed" }, { k: "source_url", label: "Source" }]} />
        : <Empty label="No snapshot loaded yet — download the template, fill it with compliantly observed public prices, and upload it here." />}</ChartCard>
  </div>);
}

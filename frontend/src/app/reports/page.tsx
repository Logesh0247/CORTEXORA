"use client";
import { useState } from "react";
import { api, useFetch } from "@/lib/api";
import { PageHead, ChartCard, Loading, ErrorBox } from "@/components/ui";
export default function Reports() {
  const { data, error, loading, refetch } = useFetch<any>(() => api("/api/reports/executive"), []);
  const [cat, setCat] = useState("All reports");
  if (loading) return <Loading />; if (error) return <ErrorBox error={error} retry={refetch} />;
  const reports = [
    { name: "Executive Report", cat: "Executive", desc: "KPIs, period comparison, forecast evaluation, churn model, decision status — rendered from live computations.", live: true },
    { name: "Decision History (audit log)", cat: "Decisions", desc: "Every recommendation, decision and outcome. Available in Decision Intelligence / Streamlit Reports.", live: false },
    { name: "Reorder Plan", cat: "Operations", desc: "Forecast-based inventory actions. Available in Demand Forecasting.", live: false },
    { name: "Churn Risk Worklist", cat: "Customers", desc: "Ranked customer risk list. Available in Customer Intelligence.", live: false }];
  const view = reports.filter((r) => cat === "All reports" || r.cat === cat);
  function download() {
    const blob = new Blob([data.markdown], { type: "text/markdown" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "cortexora_executive_report.md"; a.click();
  }
  return (<div>
    <PageHead title="Reports" question="Share it" desc="Reports render the same computed values as the dashboards — no hand-typed figures." />
    <div className="flex gap-2 mb-4 flex-wrap">{["All reports", "Executive", "Decisions", "Operations", "Customers"].map((c) => <button key={c} className={`chip ${cat === c ? "on" : ""}`} onClick={() => setCat(c)}>{c}</button>)}</div>
    <div className="grid gap-3 mb-4" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(240px,1fr))" }}>
      {view.map((r) => (<div key={r.name} className="card card-hover p-4"><div className="lab">{r.cat}</div>
        <h3 className="font-bold mt-1">{r.name}</h3><p className="mut text-[13px] mt-1">{r.desc}</p>
        {r.live ? <button className="btn primary mt-3" onClick={download}>⬇ Download (Markdown)</button>
          : <span className="chip mt-3 inline-block" style={{ cursor: "default" }}>Generated in its module</span>}</div>))}
      {!view.length && <p className="mut">No reports in this category.</p>}</div>
    <ChartCard title="Executive Report — preview" sub="Exactly what the download contains">
      <pre className="text-[13px]" style={{ whiteSpace: "pre-wrap", lineHeight: 1.6, maxHeight: 480, overflowY: "auto" }}>{data.markdown}</pre></ChartCard>
  </div>);
}

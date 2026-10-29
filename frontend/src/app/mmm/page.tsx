"use client";
import Link from "next/link";
import { api, useFetch } from "@/lib/api";
import { PageHead, ChartCard, Loading, ErrorBox, DataTable } from "@/components/ui";
export default function MMM() {
  const m = useFetch<any>(() => api("/api/mmm"), []); const mk = useFetch<any>(() => api("/api/marketing"), []);
  if (m.loading) return <Loading />; if (m.error) return <ErrorBox error={m.error} retry={m.refetch} />;
  const passed = m.data.readiness.filter((r: any) => r.Met).length;
  return (<div>
    <PageHead title="Marketing Mix Modeling" question="Prediction & planning" desc="MMM estimates channel contributions from aggregate spend/outcome history — only when the data can identify it." />
    <div className="card p-5 mb-4" style={{ borderColor: "var(--warn)" }}>
      <h3 className="font-bold" style={{ color: "var(--warn)" }}>⛔ Model not fitted — readiness gate ({passed}/{m.data.readiness.length} checks pass)</h3>
      <p className="mut text-sm mt-1">{m.data.note} Presenting fabricated channel contributions would be worse than no model; the gate below is the correct product behaviour.</p>
      <div className="mt-3"><DataTable rows={m.data.readiness} pageSize={6} columns={[
        { k: "Requirement", label: "Requirement" }, { k: "Met", label: "Met", fmt: (v: any) => v ? "✅" : "⛔" }, { k: "Evidence", label: "Evidence" }]} /></div>
      <div className="flex gap-2 mt-3"><Link className="btn primary" href="/marketing">Use the budget optimiser instead</Link>
        <Link className="btn" href="/data-sources">See what's missing in Data Sources</Link></div></div>
    {mk.data && <ChartCard title="What we CAN say today: fitted channel response curves" sub="From Marketing Intelligence — associational diminishing-returns fits, reliability-gated per channel">
      <DataTable rows={mk.data.curves} pageSize={6} columns={[{ k: "channel", label: "Channel" }, { k: "a", label: "Scale a", fmt: (v: number) => v?.toFixed(1) },
        { k: "b", label: "Elasticity b", fmt: (v: number) => v?.toFixed(2) }, { k: "r2", label: "R²", fmt: (v: number) => v?.toFixed(2) },
        { k: "reliable", label: "Reliable", fmt: (v: any) => v ? "✅" : "⛔" }]} /></ChartCard>}
  </div>);
}

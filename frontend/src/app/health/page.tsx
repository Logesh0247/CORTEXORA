"use client";
import Link from "next/link";
import { api, useFetch } from "@/lib/api";
import { PageHead, KpiCard, ChartCard, Loading, ErrorBox, DataTable } from "@/components/ui";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from "recharts";
export default function Health() {
  const { data, error, loading, refetch } = useFetch<any>(() => api("/api/health-data"), []);
  if (loading) return <Loading />; if (error) return <ErrorBox error={error} retry={refetch} />;
  const runs = data.pipeline_runs || [], last = runs[0];
  const worst = data.drift?.[0];
  return (<div>
    <PageHead title="Data & Model Health" question="Can we trust this?" desc="Data drift ≠ prediction drift ≠ measured performance degradation. Only the last — on later labelled data — is evidence about accuracy." />
    <div className="grid gap-3 mb-4" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))" }}>
      <KpiCard label="Quality gate" value={data.quality_fails === 0 ? "✅ PASS" : `⛔ ${data.quality_fails} FAIL`} sub="schema · missing · duplicates · ranges" href="/data-sources" />
      <KpiCard label="Pipeline runs logged" value={runs.length} sub={last ? `last: ${last.status} · ${String(last.finished_at).slice(0, 16)}` : "none yet"} />
      <KpiCard label="Highest feature PSI" value={worst ? worst.psi.toFixed(3) : "—"} sub={worst ? `${worst.feature}: ${worst.status}` : ""} />
      <KpiCard label="Model artifact" value="churn-v1" sub="metrics in Customer Intelligence" href="/customers" /></div>
    <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(330px,1fr))" }}>
      <ChartCard title="Data-quality checks" sub="Failures block the ETL load — outputs should not be trusted until resolved">
        <DataTable rows={data.quality} pageSize={10} columns={[{ k: "check", label: "Check" },
          { k: "status", label: "Status", fmt: (v: string) => v === "PASS" ? "✅ PASS" : v === "WARN" ? "🟡 WARN" : "⛔ FAIL" }, { k: "detail", label: "Detail" }]} /></ChartCard>
      <ChartCard title="Drift (PSI) — first 18m vs last 6m" sub="A shift prompts investigation; it never proves the model broke">
        <div style={{ height: 250 }}><ResponsiveContainer><BarChart data={data.drift}>
          <CartesianGrid strokeDasharray="3 3" opacity={.25} /><XAxis dataKey="feature" /><YAxis /><Tooltip />
          <Bar dataKey="psi" radius={[6, 6, 0, 0]}>{(data.drift || []).map((d: any, i: number) => <Cell key={i} fill={d.psi > .25 ? "#fb7185" : d.psi > .1 ? "#fbbf24" : "#34d399"} />)}</Bar></BarChart></ResponsiveContainer></div>
        <DataTable rows={data.drift} pageSize={6} columns={[{ k: "feature", label: "Feature" }, { k: "psi", label: "PSI", fmt: (v: number) => v.toFixed(4) }, { k: "status", label: "Status" }]} /></ChartCard>
      <ChartCard title="Pipeline run history" sub="Every ETL run is logged, including quality-gate failures" action={<Link className="btn" href="/data-sources">Open Data Sources</Link>}>
        <DataTable rows={runs} pageSize={8} columns={[{ k: "run_id", label: "Run" }, { k: "status", label: "Status", fmt: (v: string) => v === "success" ? "✅ success" : "⛔ " + v },
          { k: "started_at", label: "Started", fmt: (v: string) => String(v).slice(0, 16) }, { k: "quality_fails", label: "Quality fails" }]} /></ChartCard>
    </div></div>);
}

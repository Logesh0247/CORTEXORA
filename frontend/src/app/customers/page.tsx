"use client";
import { useState } from "react";
import { api, money, useFetch } from "@/lib/api";
import { PageHead, KpiCard, ChartCard, Loading, ErrorBox, DataTable } from "@/components/ui";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from "recharts";
const COLORS = ["#34d399", "#fbbf24", "#fb7185"];
export default function Customers() {
  const { data, error, loading, refetch } = useFetch<any>(() => api("/api/customers"), []);
  const [sel, setSel] = useState<any>(null);
  if (loading) return <Loading />; if (error) return <ErrorBox error={error} retry={refetch} />;
  const s = data.summary, m = data.churn_model, best = m?.results?.[m.best_model];
  return (<div>
    <PageHead title="Customer Intelligence" question="What might happen next?" desc="RFM segments + a validated churn model (leakage-tested label, dummy-baseline comparison). No sensitive data beyond demo IDs." />
    <div className="grid gap-3 mb-4" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(170px,1fr))" }}>
      <KpiCard label="Total customers" value={s.customers.toLocaleString()} sub="in warehouse" />
      <KpiCard label="Active / At risk" value={`${s.active} / ${s.at_risk}`} sub="recency 90d / 91–180d" />
      <KpiCard label="Churned (heuristic)" value={s.churned_heuristic} sub=">180d inactive — heuristic, not the model" />
      <KpiCard label="Repeat-purchase rate" value={(s.repeat_rate * 100).toFixed(1) + "%"} sub="customers with 2+ orders" />
      <KpiCard label="Avg CLV (simple)" value={money(s.avg_clv)} sub="annual value × 3y horizon (assumption)" /></div>
    <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(330px,1fr))" }}>
      <ChartCard title="Segment distribution" sub="Recency-based RFM segments">
        <div style={{ height: 260 }}><ResponsiveContainer><BarChart data={data.segments}>
          <CartesianGrid strokeDasharray="3 3" opacity={.25} /><XAxis dataKey="segment" /><YAxis /><Tooltip />
          <Bar dataKey="customers" radius={[7, 7, 0, 0]}>{data.segments.map((_: any, i: number) => <Cell key={i} fill={COLORS[i % 3]} />)}</Bar></BarChart></ResponsiveContainer></div>
        {m && <p className="mut text-[13px] mt-2">Churn model <b>{m.best_model}</b> ({m.model_version}): ROC-AUC {best.roc_auc.toFixed(2)} · PR-AUC {best.pr_auc.toFixed(2)} vs baseline {m.results.baseline_majority.pr_auc.toFixed(2)} · observed churn {(m.churn_rate * 100).toFixed(1)}%. Synthetic-data metrics validate the pipeline, not real-world accuracy.</p>}</ChartCard>
      <ChartCard title="Customer table" sub="Searchable · sortable · click a customer for detail">
        <DataTable rows={data.customers_table} pageSize={9} onRow={setSel} columns={[
          { k: "customer_id", label: "ID" }, { k: "segment", label: "Segment" }, { k: "recency_days", label: "Recency (d)" },
          { k: "frequency", label: "Orders" }, { k: "monetary", label: "Value", fmt: (v: number) => money(v) },
          { k: "clv_simple", label: "CLV est.", fmt: (v: number) => money(v) }]} />
        {sel && <div className="card p-3 mt-3 text-sm">👤 <b>Customer {sel.customer_id}</b> · {sel.segment} · last order {sel.recency_days}d ago · {sel.frequency} orders · lifetime value {money(sel.monetary)}.
          <div className="mut mt-1">Suggested action: {String(sel.segment).startsWith("Churned") ? "win-back offer review (human first — a segment is a prioritisation aid, not a verdict)." : sel.segment === "At risk" ? "retention touchpoint within 2 weeks; measure via an experiment, not anecdotes." : "nurture — early access / loyalty invitation."}</div></div>}</ChartCard>
    </div></div>);
}

"use client";
import { api, money, useFetch } from "@/lib/api";
import { PageHead, KpiCard, ChartCard, Loading, ErrorBox, DataTable } from "@/components/ui";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from "recharts";
import Link from "next/link";
const COLORS = ["#38bdf8", "#818cf8", "#34d399", "#fbbf24"];
export default function Executive() {
  const g = useFetch<any>(() => api("/api/growth"), []);
  const d = useFetch<any>(() => api("/api/decisions"), []);
  if (g.loading) return <Loading />; if (g.error) return <ErrorBox error={g.error} retry={g.refetch} />;
  const k = g.data.kpis, pend = (d.data?.decisions || []).filter((x: any) => x.status === "pending");
  const target = k.revenue * 1.1;
  return (<div>
    <PageHead title="Executive Intelligence" question="Leadership scorecard" desc="Company performance vs a +10% revenue ambition (configurable target shown for planning — labelled as a target, not a result)." />
    <div className="grid gap-3 mb-4" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))" }}>
      <KpiCard label="Revenue (actual)" value={money(k.revenue)} sub="full demo period" href="/growth" />
      <KpiCard label="Revenue target (+10%)" value={money(target)} delta={Number(((k.revenue / target - 1) * 100).toFixed(1))} sub="actual vs target" />
      <KpiCard label="Profit / Margin" value={`${money(k.profit)} · ${(k.margin * 100).toFixed(1)}%`} sub="profitability" href="/pricing" />
      <KpiCard label="Open priority actions" value={pend.length} sub="awaiting leadership review" href="/decisions" />
    </div>
    <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(330px,1fr))" }}>
      <ChartCard title="Business-unit performance (category)" sub="Revenue and margin by unit — click through for drill-down">
        <div style={{ height: 280 }}><ResponsiveContainer><BarChart data={g.data.by_category}>
          <CartesianGrid strokeDasharray="3 3" opacity={.25} /><XAxis dataKey="category" /><YAxis tickFormatter={(v) => "$" + v / 1000 + "k"} /><Tooltip formatter={(v: any) => money(v)} />
          <Bar dataKey="revenue" radius={[7, 7, 0, 0]}>{g.data.by_category.map((_: any, i: number) => <Cell key={i} fill={COLORS[i % 4]} />)}</Bar></BarChart></ResponsiveContainer></div>
        <Link className="btn mt-2" href="/growth">Drill into Business Growth →</Link></ChartCard>
      <ChartCard title="Opportunity & risk summary" sub="Generated from current analytics, not hand-written">
        <ul className="text-sm space-y-2.5 mt-1">
          <li>🏆 Opportunity: <b>{g.data.by_category[0].category}</b> is the largest unit ({money(g.data.by_category[0].revenue)}) — protect its supply first.</li>
          <li>⚠️ Risk: thinnest margin sits in <b>{[...g.data.by_category].sort((a: any, b: any) => a.margin - b.margin)[0].category}</b> ({(Math.min(...g.data.by_category.map((x: any) => x.margin)) * 100).toFixed(1)}%).</li>
          <li>🧠 {pend.length} recommendations await a decision; expected-vs-actual tracking is in Decision Intelligence.</li></ul>
        <div className="flex gap-2 mt-3"><Link className="btn primary" href="/decisions">Review priorities</Link><Link className="btn" href="/forecasting">Forecast outlook</Link></div></ChartCard>
      <ChartCard title="Period comparison (30d vs prior 30d)" sub="Shared metric definitions">
        <DataTable rows={g.data.period_compare} pageSize={6} columns={[
          { k: "metric", label: "Metric" }, { k: "current", label: "Current", fmt: (v: number) => Math.round(v).toLocaleString() },
          { k: "previous", label: "Previous", fmt: (v: number) => Math.round(v).toLocaleString() },
          { k: "change_pct", label: "Change", fmt: (v: number) => <span style={{ color: v >= 0 ? "var(--good)" : "var(--bad)", fontWeight: 700 }}>{v >= 0 ? "+" : ""}{v.toFixed(1)}%</span> }]} /></ChartCard>
    </div></div>);
}

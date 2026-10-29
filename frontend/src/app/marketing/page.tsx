"use client";
import { useState } from "react";
import { api, money, useFetch } from "@/lib/api";
import { PageHead, KpiCard, ChartCard, Loading, ErrorBox, DataTable } from "@/components/ui";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from "recharts";
const COLORS = ["#38bdf8", "#818cf8", "#34d399", "#fbbf24"];
export default function Marketing() {
  const [budget, setBudget] = useState(3300);
  const { data, error, loading, refetch } = useFetch<any>(() => api(`/api/marketing?budget=${budget}`), [budget]);
  if (loading && !data) return <Loading />; if (error) return <ErrorBox error={error} retry={refetch} />;
  const ch = data.channels, totSpend = ch.reduce((a: number, x: any) => a + x.spend, 0), totConv = ch.reduce((a: number, x: any) => a + x.conversions, 0);
  const best = [...ch].sort((a: any, b: any) => a.cac_proxy - b.cac_proxy)[0];
  const comp = Object.keys(data.optimizer.allocation || {}).map((c) => ({ channel: c, current: Math.round(data.optimizer.current_allocation[c]), optimized: Math.round(data.optimizer.allocation[c]) }));
  return (<div>
    <PageHead title="Marketing Intelligence" question="What happened? Why?" desc="CAC is a spend/conversions proxy. ROAS is intentionally not shown — no attribution join exists, and attributed ≠ incremental." />
    <div className="grid gap-3 mb-4" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))" }}>
      <KpiCard label="Total spend" value={money(totSpend)} sub={`${ch.length} channels`} />
      <KpiCard label="Conversions" value={totConv.toLocaleString()} sub="all channels" />
      <KpiCard label="Blended CAC (proxy)" value={money(totSpend / Math.max(totConv, 1))} sub="spend / conversion" />
      <KpiCard label="Best CAC channel" value={best.channel} sub={`${money(best.cac_proxy)} per conversion`} /></div>
    <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(330px,1fr))" }}>
      <ChartCard title="Channel comparison" sub="Spend by channel">
        <div style={{ height: 270 }}><ResponsiveContainer><BarChart data={ch}>
          <CartesianGrid strokeDasharray="3 3" opacity={.25} /><XAxis dataKey="channel" /><YAxis tickFormatter={(v) => "$" + v / 1000 + "k"} /><Tooltip formatter={(v: any) => money(v)} />
          <Bar dataKey="spend" radius={[7, 7, 0, 0]}>{ch.map((_: any, i: number) => <Cell key={i} fill={COLORS[i % 4]} />)}</Bar></BarChart></ResponsiveContainer></div>
        <DataTable rows={ch} pageSize={6} columns={[{ k: "channel", label: "Channel" }, { k: "spend", label: "Spend", fmt: (v: number) => money(v) },
          { k: "conversions", label: "Conv." }, { k: "cac_proxy", label: "CAC", fmt: (v: number) => money(v) },
          { k: "conversion_rate", label: "Conv. rate", fmt: (v: number) => (v * 100).toFixed(2) + "%" }]} /></ChartCard>
      <div className="card p-4"><h3 className="font-bold">🎯 Budget allocation scenario</h3>
        <p className="mut text-[13px]">Fitted diminishing-returns curves (associational, not causal incrementality). Reliability-gated per channel.</p>
        <label className="lab">Total weekly budget — ${budget.toLocaleString()}</label>
        <input type="range" min={500} max={10000} step={100} value={budget} onChange={(e) => setBudget(+e.target.value)} className="w-full" />
        <div className="text-[15px] mt-1">Expected conversion change <b style={{ color: "var(--good)" }}>{data.optimizer.expected_gain_pct >= 0 ? "+" : ""}{data.optimizer.expected_gain_pct?.toFixed(1)}%</b> at the same budget</div>
        <div style={{ height: 230, marginTop: 8 }}><ResponsiveContainer><BarChart data={comp}>
          <CartesianGrid strokeDasharray="3 3" opacity={.25} /><XAxis dataKey="channel" /><YAxis /><Tooltip formatter={(v: any) => money(v)} />
          <Bar dataKey="current" fill="#64748b" radius={[5, 5, 0, 0]} /><Bar dataKey="optimized" fill="#38bdf8" radius={[5, 5, 0, 0]} /></BarChart></ResponsiveContainer></div>
        <DataTable rows={data.curves} pageSize={6} columns={[{ k: "channel", label: "Channel" }, { k: "b", label: "Elasticity b", fmt: (v: number) => v?.toFixed(2) },
          { k: "r2", label: "Fit R²", fmt: (v: number) => v?.toFixed(2) }, { k: "reliable", label: "Reliable", fmt: (v: any) => v ? "✅" : "⛔ gated" }]} /></div>
    </div></div>);
}

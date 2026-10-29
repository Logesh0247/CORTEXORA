"use client";
import { useState } from "react";
import { api, money, useFetch } from "@/lib/api";
import { PageHead, KpiCard, ChartCard, Loading, ErrorBox, DataTable } from "@/components/ui";
import { ComposedChart, Area, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts";
export default function Forecasting() {
  const [cat, setCat] = useState("Electronics"); const [horizon, setHorizon] = useState(8); const [growth, setGrowth] = useState(0);
  const { data, error, loading, refetch } = useFetch<any>(() => api(`/api/forecast?category=${cat}&horizon=${horizon}`), [cat, horizon]);
  if (loading && !data) return <Loading />; if (error) return <ErrorBox error={error} retry={refetch} />;
  const ev = data.evaluation, better = ev.moving_average_4w.WAPE < ev.seasonal_naive.WAPE;
  const chart = [...data.history.map((h: any) => ({ week: h.week, actual: h.actual })),
    ...data.forecast.map((f: any) => ({ week: f.week, forecast: Math.round(f.forecast * (1 + growth / 100)), band: [Math.round(f.lower * (1 + growth / 100)), Math.round(f.upper * (1 + growth / 100))] }))];
  const high = data.reorder_plan.filter((r: any) => r.stockout_risk === "High");
  return (<div>
    <PageHead title="Demand Forecasting" question="What might happen next?" desc="Actuals, predictions and simulated scenarios are kept visually and verbally distinct. Accuracy is measured on a chronological hold-out vs a seasonal-naive baseline."
      actions={<><select value={cat} onChange={(e) => setCat(e.target.value)}>{data.categories.map((c: string) => <option key={c}>{c}</option>)}</select>
        <select value={horizon} onChange={(e) => setHorizon(+e.target.value)}>{[4, 8, 12, 16].map((h) => <option key={h} value={h}>{h} weeks</option>)}</select></>} />
    <div className="grid gap-3 mb-4" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(190px,1fr))" }}>
      <KpiCard label="Model WAPE (hold-out)" value={(ev.moving_average_4w.WAPE * 100).toFixed(1) + "%"} sub={better ? "beats the baseline" : "⚠️ does NOT beat baseline"} />
      <KpiCard label="Seasonal-naive WAPE" value={(ev.seasonal_naive.WAPE * 100).toFixed(1) + "%"} sub="the bar every forecast must clear" />
      <KpiCard label="High stockout-risk products" value={high.length} sub="across all categories" href="/decisions" />
      <KpiCard label="Scenario demand growth" value={(growth > 0 ? "+" : "") + growth + "%"} sub="simulation lever →" /></div>
    <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(340px,1fr))" }}>
      <ChartCard title={`${cat} — history, forecast & 80% interval`} sub="Solid = actuals · dashed blue = forecast · band = uncertainty interval" action={
        <label className="text-[13px] mut">Scenario growth <input type="range" min={-30} max={50} value={growth} onChange={(e) => setGrowth(+e.target.value)} style={{ verticalAlign: "middle" }} /> {growth}%</label>}>
        <div style={{ height: 320 }}><ResponsiveContainer><ComposedChart data={chart}>
          <CartesianGrid strokeDasharray="3 3" opacity={.25} /><XAxis dataKey="week" tick={{ fontSize: 10 }} minTickGap={50} /><YAxis tick={{ fontSize: 11 }} /><Tooltip /><Legend />
          <Area dataKey="band" stroke="none" fill="#38bdf8" fillOpacity={.16} name="80% interval" />
          <Line dataKey="actual" stroke="#e9f1fc" strokeWidth={2.2} dot={false} name="Actual" />
          <Line dataKey="forecast" stroke="#38bdf8" strokeWidth={2.6} strokeDasharray="6 4" dot={false} name="Forecast (scenario-adjusted)" /></ComposedChart></ResponsiveContainer></div>
        <p className="mut text-[13px]">Train ended {ev.train_end}. If the model does not beat the baseline for a category, purchasing should not follow the forecast — the table tells you which case you are in.</p></ChartCard>
      <ChartCard title="📦 Reorder plan (95% service level)" sub="Forecast-based · click Decision Intelligence to act on these">
        <DataTable rows={data.reorder_plan} pageSize={9} columns={[
          { k: "product_id", label: "ID" }, { k: "category", label: "Category" }, { k: "stock_on_hand", label: "Stock" },
          { k: "recommended_reorder_qty", label: "Reorder" }, { k: "estimated_order_cost", label: "Est. cost", fmt: (v: number) => money(v) },
          { k: "stockout_risk", label: "Risk", fmt: (v: string) => v === "High" ? "🔴 High" : v === "Medium" ? "🟡 Med" : "🟢 Low" }]} /></ChartCard>
    </div></div>);
}

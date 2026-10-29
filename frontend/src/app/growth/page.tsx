"use client";
import { useState } from "react";
import { api, money, useFetch } from "@/lib/api";
import { PageHead, KpiCard, ChartCard, Loading, ErrorBox, DataTable } from "@/components/ui";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from "recharts";
const COLORS = ["#38bdf8", "#818cf8", "#34d399", "#fbbf24"];
export default function Growth() {
  const { data, error, loading, refetch } = useFetch<any>(() => api("/api/growth"), []);
  const [dim, setDim] = useState("by_category"); const [sel, setSel] = useState<any>(null);
  if (loading) return <Loading />; if (error) return <ErrorBox error={error} retry={refetch} />;
  const k = data.kpis, pc = Object.fromEntries(data.period_compare.map((x: any) => [x.metric, x.change_pct]));
  const rows = data[dim];
  return (<div>
    <PageHead title="Business Growth Intelligence" question="What happened? Why?" desc="Shared metric definitions across every module. Click a bar or row to inspect." />
    <div className="grid gap-3 mb-4" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(170px,1fr))" }}>
      <KpiCard label="Revenue" value={money(k.revenue)} delta={pc.revenue} sub="vs prior 30d" />
      <KpiCard label="Profit" value={money(k.profit)} delta={pc.profit} sub="vs prior 30d" />
      <KpiCard label="Margin" value={(k.margin * 100).toFixed(1) + "%"} sub="profit / revenue" />
      <KpiCard label="Orders" value={k.orders.toLocaleString()} delta={pc.orders} sub="vs prior 30d" />
      <KpiCard label="Avg order value" value={money(k.aov)} delta={pc.aov} sub="vs prior 30d" /></div>
    <div className="card p-3 mb-4 flex gap-2 items-center"><span className="lab">View</span>
      {[["by_category", "By category"], ["by_region", "By region"]].map(([v, l]) => <button key={v} className={`chip ${dim === v ? "on" : ""}`} onClick={() => setDim(v)}>{l}</button>)}
      <span className="mut text-sm">Tables support sort · search · pagination.</span></div>
    <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(330px,1fr))" }}>
      <ChartCard title={dim === "by_category" ? "Category performance" : "Region performance"} sub="Click a segment to inspect it below">
        <div style={{ height: 280 }}><ResponsiveContainer><BarChart data={rows}>
          <CartesianGrid strokeDasharray="3 3" opacity={.25} /><XAxis dataKey={dim === "by_category" ? "category" : "region"} /><YAxis tickFormatter={(v) => "$" + v / 1000 + "k"} /><Tooltip formatter={(v: any) => money(v)} />
          <Bar dataKey="revenue" radius={[7, 7, 0, 0]} cursor="pointer" onClick={(e: any) => setSel(e)}>
            {rows.map((_: any, i: number) => <Cell key={i} fill={COLORS[i % 4]} />)}</Bar></BarChart></ResponsiveContainer></div>
        {sel && <div className="card p-3 mt-2 text-sm">🔎 <b>{sel.category || sel.region}</b> · revenue {money(sel.revenue)} · profit {money(sel.profit)} · margin {(sel.margin * 100).toFixed(1)}%</div>}</ChartCard>
      <ChartCard title="Segment table" sub="Underperformers sink to the bottom when you sort by margin">
        <DataTable rows={rows} pageSize={8} columns={[
          { k: dim === "by_category" ? "category" : "region", label: "Segment" }, { k: "revenue", label: "Revenue", fmt: (v: number) => money(v) },
          { k: "profit", label: "Profit", fmt: (v: number) => money(v) }, { k: "margin", label: "Margin", fmt: (v: number) => (v * 100).toFixed(1) + "%" },
          ...(dim === "by_category" ? [{ k: "orders", label: "Orders" }, { k: "units", label: "Units" }] : [])]} /></ChartCard>
      <ChartCard title="Top products" sub="From the live dashboard API">
        <DataTable rows={data.products} pageSize={8} columns={[
          { k: "product_name", label: "Product" }, { k: "category", label: "Category" }, { k: "revenue", label: "Revenue", fmt: (v: number) => money(v) },
          { k: "margin", label: "Margin", fmt: (v: number) => (v * 100).toFixed(1) + "%" }]} /></ChartCard>
    </div></div>);
}

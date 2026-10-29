"use client";
import { useEffect, useState } from "react";
import { api, money, useFetch } from "@/lib/api";
import { PageHead, KpiCard, ChartCard, Loading, ErrorBox, DataTable } from "@/components/ui";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceDot } from "recharts";
export default function Pricing() {
  const [product, setProduct] = useState(""); const [chg, setChg] = useState(10); const [elas, setElas] = useState(-1.2);
  const { data, error, loading, refetch } = useFetch<any>(() => api(`/api/pricing?product=${encodeURIComponent(product)}&change=${chg}&elasticity=${elas}`), [product, chg, elas]);
  useEffect(() => { if (data && !product) setProduct(data.product.name); }, [data, product]);
  if (loading && !data) return <Loading />; if (error) return <ErrorBox error={error} retry={refetch} />;
  const s = data.scenario, sweep = Array.from({ length: 31 }, (_, i) => { const c = -30 + i * 2; return { c, rev: s.observed_revenue / (1 + s.elasticity * s.change_pct / 100) / (1 + s.change_pct / 100) * (1 + s.elasticity * c / 100) * (1 + c / 100) }; });
  return (<div>
    <PageHead title="Pricing & Profitability" question="What should we do?" desc="Assumption-based simulator — elasticity is your input, results are scenarios, never proven causal effects." />
    <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(320px,1fr))" }}>
      <div className="card p-4"><h3 className="font-bold mb-3">🎛️ Scenario controls</h3>
        <label className="lab">Product</label>
        <select value={product} onChange={(e) => setProduct(e.target.value)} className="w-full mb-3">{data.products.map((p: string) => <option key={p}>{p}</option>)}</select>
        <label className="lab">Price change {chg > 0 ? "+" : ""}{chg}%</label>
        <input type="range" min={-30} max={30} value={chg} onChange={(e) => setChg(+e.target.value)} className="w-full" />
        <label className="lab">Assumed elasticity {elas}</label>
        <input type="range" min={-3} max={-0.1} step={0.1} value={elas} onChange={(e) => setElas(+e.target.value)} className="w-full" />
        <p className="mut text-[13px] mt-2">{data.product.name}: list {money(data.product.list_price)} · unit cost {money(data.product.unit_cost)} · contribution {money(data.product.list_price - data.product.unit_cost)}/unit.</p>
        <p className="mut text-[13px]">Break-even at $10k fixed cost: <b>{data.breakeven_units_at_10000_fixed === Infinity || !isFinite(data.breakeven_units_at_10000_fixed) ? "never (contribution ≤ 0)" : Math.ceil(data.breakeven_units_at_10000_fixed).toLocaleString() + " units"}</b></p></div>
      <ChartCard title="Scenario outcome" sub={s.label}>
        <div className="grid gap-3 mb-3" style={{ gridTemplateColumns: "1fr 1fr" }}>
          <KpiCard label="Scenario revenue" value={money(s.scenario_revenue)} delta={Number(s.delta_pct.toFixed(1))} sub="vs observed (24m)" />
          <KpiCard label="Observed revenue" value={money(s.observed_revenue)} sub="actual recorded sales" /></div>
        <div style={{ height: 240 }}><ResponsiveContainer><LineChart data={sweep}>
          <CartesianGrid strokeDasharray="3 3" opacity={.25} /><XAxis dataKey="c" tickFormatter={(v) => v + "%"} /><YAxis tickFormatter={(v) => "$" + Math.round(v / 1000) + "k"} />
          <Tooltip formatter={(v: any) => money(v)} labelFormatter={(v) => `Price ${v}%`} />
          <Line dataKey="rev" stroke="#38bdf8" strokeWidth={2.4} dot={false} />
          <ReferenceDot x={chg - (chg % 2)} y={sweep.find((x) => x.c === chg - (chg % 2))?.rev} r={6} fill="#fbbf24" /></LineChart></ResponsiveContainer></div></ChartCard>
      <ChartCard title="Discount effectiveness (observed)" sub="Association only — discounted baskets differ; this is not a causal discount effect">
        <DataTable rows={data.discount_effectiveness} pageSize={6} columns={[
          { k: "discount_bucket", label: "Bucket" }, { k: "revenue", label: "Revenue", fmt: (v: number) => money(v) },
          { k: "margin", label: "Margin", fmt: (v: number) => (v * 100).toFixed(1) + "%" },
          { k: "revenue_share", label: "Rev share", fmt: (v: number) => (v * 100).toFixed(1) + "%" }]} /></ChartCard>
    </div></div>);
}

"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, BarChart, Bar, Cell, PieChart, Pie, Legend } from "recharts";
import { api, money, useFetch } from "@/lib/api";
import { PageHead, KpiCard, ChartCard, Loading, ErrorBox, DataTable } from "@/components/ui";

const CATS = ["Electronics", "Apparel", "Home", "Beauty"], REGS = ["North", "South", "East", "West"], CHANS = ["Online", "Store", "Marketplace"];
const COLORS = ["#38bdf8", "#818cf8", "#34d399", "#fbbf24", "#fb7185", "#22d3ee"];
const hour = new Date().getHours();
const GREET = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

export default function Home() {
  const router = useRouter();
  const [days, setDays] = useState(10000);
  const [metric, setMetric] = useState("Revenue");
  const [gran, setGran] = useState("Weekly");
  const [breakdown, setBreakdown] = useState("Total");
  const [cats, setCats] = useState<string[]>(CATS);
  const [selCat, setSelCat] = useState<string | null>(null);
  const [price, setPrice] = useState(5); const [demand, setDemand] = useState(10); const [disc, setDisc] = useState(2);
  const [selProd, setSelProd] = useState<any>(null);

  useEffect(() => {
    const saved = Number(localStorage.getItem("cx-days") || 10000); if (saved) setDays(saved);
    const h = (e: any) => setDays(Number(e.detail));
    window.addEventListener("cx-days", h); return () => window.removeEventListener("cx-days", h);
  }, []);
  const q = `/api/dashboard?days=${days}&metric=${metric}&gran=${gran}&breakdown=${breakdown}&cats=${cats.join(",")}&regs=${REGS.join(",")}&chans=${CHANS.join(",")}`;
  const { data, error, loading, refetch } = useFetch<any>(() => api(q), [q]);
  const dec = useFetch<any>(() => api("/api/decisions"), []);
  const fc = useFetch<any>(() => api("/api/forecast?category=Electronics"), []);

  const trendData = useMemo(() => {
    if (!data) return [];
    return data.trend.labels.map((l: string, i: number) => {
      const row: any = { label: l };
      data.trend.series.forEach((s: any) => { row[s.name] = s.data[i]; });
      return row;
    });
  }, [data]);
  const products = useMemo(() => (data?.products || []).filter((p: any) => !selCat || p.category === selCat), [data, selCat]);
  const highRisk = (fc.data?.reorder_plan || []).filter((r: any) => r.stockout_risk === "High").length;

  if (loading && !data) return <Loading />;
  if (error && !data) return <ErrorBox error={error} retry={refetch} />;
  const k = data.kpis, ins = data.insights;
  const scenRev = k.revenue * (1 + price / 100) * (1 + demand / 100) + k.revenue * (disc / 100) * 0.35;
  const scenProf = k.profit * (1 + price / 100) * (1 + demand / 100) + k.revenue * (disc / 100) * 0.35;
  const pending = (dec.data?.decisions || []).filter((d: any) => d.status === "pending").slice(0, 3);

  return (<div>
    <PageHead title={`${GREET} — Executive Overview`} question="What happened · what next · what to do"
      desc="CORTEXORA command centre. Demo dataset (synthetic, seed=42) · every figure computed live by the Python analytics API."
      actions={<>
        <button className="btn" onClick={() => window.dispatchEvent(new Event("cx-open-copilot"))}>🤖 Ask Copilot</button>
        <Link className="btn primary" href="/decisions">🧠 Review decisions{pending.length ? ` (${pending.length})` : ""}</Link></>} />

    <div className="card p-3.5 mb-4 flex flex-wrap items-center gap-2 sticky top-[64px] z-30">
      <span className="lab">Period</span>
      {[["30D", 30], ["90D", 90], ["6M", 182], ["1Y", 365], ["All", 10000]].map(([l, v]: any) => (
        <button key={l} className={`chip ${days === v ? "on" : ""}`} onClick={() => setDays(v)}>{l}</button>))}
      <span className="lab ml-3">Metric</span>
      <select value={metric} onChange={(e) => setMetric(e.target.value)}>{["Revenue", "Profit", "Units", "Orders"].map((m) => <option key={m}>{m}</option>)}</select>
      <span className="lab">Granularity</span>
      <select value={gran} onChange={(e) => setGran(e.target.value)}>{["Weekly", "Daily", "Monthly"].map((m) => <option key={m}>{m}</option>)}</select>
      <span className="lab">Split</span>
      <select value={breakdown} onChange={(e) => setBreakdown(e.target.value)}>{["Total", "Category", "Region", "Channel"].map((m) => <option key={m}>{m}</option>)}</select>
      <span className="lab ml-3">Categories</span>
      {CATS.map((c) => <button key={c} className={`chip ${cats.includes(c) ? "on" : ""}`} onClick={() => setCats(cats.includes(c) ? cats.filter((x) => x !== c) : [...cats, c])}>{c}</button>)}
    </div>

    <div className="grid gap-3 mb-4" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))" }}>
      <KpiCard label="Total Revenue" value={money(k.revenue)} delta={k.revenue_delta} sub="vs prior period · shared metric definition" href="/growth" title="Revenue = Σ qty × unit_price × (1−discount)" />
      <KpiCard label="Net Profit" value={money(k.profit)} delta={k.profit_delta} sub="after product cost" href="/growth" title="Profit = revenue − Σ qty × unit_cost" />
      <KpiCard label="Profit Margin" value={(k.margin * 100).toFixed(1) + "%"} sub="profit / revenue" href="/pricing" />
      <KpiCard label="Total Orders" value={k.orders.toLocaleString()} delta={k.orders_delta} sub={`${k.customers} customers in scope`} href="/growth" />
      <KpiCard label="Forecast outlook (Electronics, 8w)" value={fc.data ? money(fc.data.forecast.reduce((a: number, x: any) => a + x.forecast, 0) * 190) : "…"} sub="units forecast × avg price — see Forecasting for evidence" href="/forecasting" />
    </div>

    <div className="grid gap-4 mb-4" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(320px,1fr))" }}>
      <ChartCard title={`${metric} trend`} sub={`${gran}${breakdown !== "Total" ? " · by " + breakdown : ""} · actuals only (forecast lives in Demand Forecasting)`}>
        <div style={{ height: 300 }}><ResponsiveContainer><AreaChart data={trendData}>
          <CartesianGrid strokeDasharray="3 3" opacity={.25} /><XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={40} /><YAxis tick={{ fontSize: 11 }} />
          <Tooltip formatter={(v: any) => Math.round(v).toLocaleString()} />
          {breakdown !== "Total" && <Legend />}
          {data.trend.series.map((s: any, i: number) => <Area key={s.name} dataKey={s.name} stroke={COLORS[i % 6]} fill={COLORS[i % 6]} fillOpacity={.18} strokeWidth={2.2} />)}
        </AreaChart></ResponsiveContainer></div>
      </ChartCard>
      <div className="card p-4">
        <h3 className="font-bold">🧪 Scenario Lab</h3>
        <p className="mut text-[13px] mb-3">Assumption-based simulation on the current scope — not a guaranteed prediction.</p>
        <label className="lab">Price change {price > 0 ? "+" : ""}{price}%</label>
        <input type="range" min={-20} max={30} value={price} onChange={(e) => setPrice(+e.target.value)} className="w-full" />
        <label className="lab">Demand change {demand > 0 ? "+" : ""}{demand}%</label>
        <input type="range" min={-30} max={50} value={demand} onChange={(e) => setDemand(+e.target.value)} className="w-full" />
        <label className="lab">Discount reduction {disc} pts</label>
        <input type="range" min={0} max={10} value={disc} onChange={(e) => setDisc(+e.target.value)} className="w-full" />
        <div className="mt-2 text-[15px]">Projected revenue <b className="text-xl">{money(scenRev)}</b> <span style={{ color: scenRev >= k.revenue ? "var(--good)" : "var(--bad)", fontWeight: 800 }}>{k.revenue ? ((scenRev / k.revenue - 1) * 100).toFixed(1) : 0}%</span></div>
        <div className="text-[15px]">Projected profit <b className="text-xl">{money(scenProf)}</b></div>
        <button className="btn mt-3" onClick={() => router.push("/pricing")}>Test properly in Pricing →</button>
      </div>
    </div>

    <div className="grid gap-4 mb-4" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(320px,1fr))" }}>
      <ChartCard title="Sales by category — click a bar to filter the leaderboard" sub={selCat ? `Filtered to ${selCat} (click again to clear)` : "Drill-down: selection filters products below"}>
        <div style={{ height: 260 }}><ResponsiveContainer><BarChart data={data.categories}>
          <CartesianGrid strokeDasharray="3 3" opacity={.25} /><XAxis dataKey="name" tick={{ fontSize: 12 }} /><YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => "$" + (v / 1000) + "k"} />
          <Tooltip formatter={(v: any) => money(v)} />
          <Bar dataKey="value" radius={[7, 7, 0, 0]} onClick={(e: any) => setSelCat(selCat === e.name ? null : e.name)} cursor="pointer">
            {data.categories.map((c: any, i: number) => <Cell key={i} fill={COLORS[i % 6]} opacity={selCat && selCat !== c.name ? .35 : 1} />)}</Bar>
        </BarChart></ResponsiveContainer></div>
      </ChartCard>
      <ChartCard title="Regional mix" sub="Share of the selected metric in current scope">
        <div style={{ height: 260 }}><ResponsiveContainer><PieChart>
          <Pie data={data.regions} dataKey="value" nameKey="name" innerRadius={58} outerRadius={92} paddingAngle={2}>
            {data.regions.map((r: any, i: number) => <Cell key={i} fill={COLORS[i % 6]} />)}</Pie>
          <Tooltip formatter={(v: any) => money(v)} /><Legend /></PieChart></ResponsiveContainer></div>
      </ChartCard>
      <div className="card p-4">
        <h3 className="font-bold">🚨 Business alerts & insights</h3>
        <div className="space-y-3 mt-2 text-sm">
          <div>⚠️ <b>{highRisk} products</b> at high stockout risk in the current reorder plan.
            <div className="flex gap-2 mt-1"><Link className="btn" href="/forecasting">Investigate</Link>
            <button className="btn" onClick={() => window.dispatchEvent(new Event("cx-open-copilot"))}>Ask Copilot</button></div></div>
          <div>🏆 <b>{ins.top_category}</b> leads revenue ({money(ins.top_category_value)}); <b>{ins.top_region}</b> is the strongest region.</div>
          <div>📉 Margin watch: <b>{ins.margin_watch}</b> has the thinnest margin in scope — review discounting before pushing volume there.
            <div className="mt-1"><Link className="btn" href="/pricing">Open Pricing</Link></div></div>
          <div>🧠 <b>{pending.length} priority actions</b> awaiting review in Decision Intelligence.</div>
        </div>
      </div>
    </div>

    <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(340px,1fr))" }}>
      <ChartCard title={`🏆 Product leaderboard${selCat ? " — " + selCat : ""}`} sub="Sort, search, paginate · click a row for detail">
        <DataTable rows={products} pageSize={8} onRow={setSelProd} columns={[
          { k: "product_name", label: "Product" }, { k: "category", label: "Category" },
          { k: "revenue", label: "Revenue", fmt: (v: number) => money(v) },
          { k: "margin", label: "Margin", fmt: (v: number) => (v * 100).toFixed(1) + "%" },
          { k: "units", label: "Units", fmt: (v: number) => Math.round(v).toLocaleString() }]} />
        {selProd && (<div className="card p-3 mt-3 text-sm">📦 <b>{selProd.product_name}</b> ({selProd.category}) · revenue <b>{money(selProd.revenue)}</b> · profit {money(selProd.profit)} · margin {(selProd.margin * 100).toFixed(1)}% · {Math.round(selProd.units).toLocaleString()} units · {selProd.orders} orders.
          <div className="flex gap-2 mt-2"><Link className="btn" href="/forecasting">Forecast category</Link><Link className="btn" href="/pricing">Price scenario</Link></div></div>)}
      </ChartCard>
      <ChartCard title="🧠 Priority actions" sub="Highest-priority pending recommendations from the Decision Engine" action={<Link className="btn primary" href="/decisions">Open workspace</Link>}>
        {pending.length ? pending.map((d: any) => (
          <div key={d.recommendation_id} className="card p-3 mb-2.5">
            <div className="text-sm"><b>{d.area}</b> · priority {d.priority} — {d.problem}</div>
            <div className="mut text-[13px] mt-0.5">→ {d.action}</div>
            <div className="flex gap-2 mt-2"><Link className="btn" href="/decisions">Inspect & decide</Link>
              <button className="btn" onClick={() => window.dispatchEvent(new Event("cx-open-copilot"))}>Ask Copilot</button></div></div>))
          : <p className="mut text-sm">No pending recommendations — generate them in Decision Intelligence.</p>}
      </ChartCard>
    </div>
  </div>);
}

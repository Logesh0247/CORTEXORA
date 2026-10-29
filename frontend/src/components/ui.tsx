"use client";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowDownRight, ArrowUpRight, Info, Loader2, AlertTriangle, Inbox } from "lucide-react";

export function PageHead({ title, question, desc, actions }: any) {
  return (<div className="mb-5">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div><h1 className="text-[26px] font-extrabold tracking-tight">{title}</h1>
        <div className="mt-1.5 flex flex-wrap items-center gap-2.5">
          <span className="chip on" style={{ cursor: "default" }}>{question}</span>
          <span className="mut text-sm">{desc}</span></div></div>
      <div className="flex gap-2">{actions}</div></div></div>);
}

export function Sparkline({ data, color = "var(--a)", w = 96, h = 28 }: { data: number[]; color?: string; w?: number; h?: number }) {
  if (!data || data.length < 2) return null;
  const min = Math.min(...data), max = Math.max(...data), span = max - min || 1;
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - 3 - ((v - min) / span) * (h - 6)}`).join(" ");
  return (<svg width={w} height={h} aria-hidden="true" style={{ display: "block" }}>
    <polyline points={pts} fill="none" stroke={color} strokeWidth="1.8" strokeLinejoin="round" strokeLinecap="round" opacity=".9" />
    <polyline points={`0,${h} ${pts} ${w},${h}`} fill={color} stroke="none" opacity=".10" /></svg>);
}

export function KpiCard({ label, value, delta, sub, href, title, spark, invert }: any) {
  const goodDir = invert ? (delta ?? 0) <= 0 : (delta ?? 0) >= 0;
  const inner = (<>
    <div className="flex items-start justify-between gap-2">
      <div className="lab flex items-center gap-1.5">{label}{title && <span title={title} aria-label={title}><Info size={12} /></span>}</div>
      {spark && <Sparkline data={spark} color={typeof delta === "number" ? (goodDir ? "var(--good)" : "var(--bad)") : "var(--a)"} />}
    </div>
    <div className="kpi-val mt-1.5 text-[25px] font-extrabold tracking-tight leading-none">{value}</div>
    <div className="mt-1.5 text-[12.5px] mut flex items-center gap-1 flex-wrap">
      {typeof delta === "number" && (<span style={{ color: goodDir ? "var(--good)" : "var(--bad)", fontWeight: 750, display: "inline-flex", alignItems: "center", gap: 1 }}>
        {delta >= 0 ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />} {Math.abs(delta)}%</span>)}
      {sub}</div></>);
  const cls = "card card-hover p-4 block";
  return href ? <Link href={href} className={cls}>{inner}</Link> : <div className={cls}>{inner}</div>;
}

export function StatusBadge({ status }: { status: string }) {
  const s = String(status || "").toLowerCase();
  const map: Record<string, string> = { pass: "var(--good)", success: "var(--good)", approved: "var(--good)", measured: "var(--c)", stable: "var(--good)", ok: "var(--good)", pending: "var(--warn)", warn: "var(--warn)", deferred: "var(--warn)", "at risk": "var(--warn)", moderate: "var(--warn)", fail: "var(--bad)", rejected: "var(--bad)", high: "var(--bad)", significant: "var(--bad)" };
  const col = map[s] || "var(--mut)";
  return <span className="inline-flex items-center gap-1.5 text-[12px] font-semibold" style={{ color: col }}><span className="status-dot" style={{ background: col }} />{status}</span>;
}

export function Tabs({ tabs, active, onChange }: any) {
  return (<div className="inline-flex gap-1 p-1 rounded-[10px]" style={{ background: "var(--panel2)", border: "1px solid var(--line)" }} role="tablist">
    {tabs.map((t: string) => <button key={t} role="tab" aria-selected={active === t} onClick={() => onChange(t)}
      className="px-3 py-1.5 rounded-lg text-[13px] font-semibold transition-all"
      style={active === t ? { background: "var(--panel)", color: "var(--txt)", boxShadow: "var(--shadow)", border: "1px solid var(--line)" } : { color: "var(--mut)", border: "1px solid transparent", background: "none" }}>{t}</button>)}
  </div>);
}

/* ---- toast system: call toast("Saved") anywhere; <Toaster/> lives in the shell ---- */
export function toast(msg: string) { if (typeof window !== "undefined") window.dispatchEvent(new CustomEvent("cx-toast", { detail: msg })); }
export function Toaster() {
  const [items, setItems] = useState<any[]>([]);
  useEffect(() => {
    const h = (e: any) => {
      const id = Math.random().toString(36).slice(2);
      setItems((x) => [...x, { id, msg: e.detail }]);
      setTimeout(() => setItems((x) => x.filter((i) => i.id !== id)), 3600);
    };
    window.addEventListener("cx-toast", h);
    return () => window.removeEventListener("cx-toast", h);
  }, []);
  return (<div style={{ position: "fixed", bottom: 84, right: 20, zIndex: 90, display: "flex", flexDirection: "column", gap: 8 }} aria-live="polite">
    {items.map((i) => <div key={i.id} className="toast card px-4 py-2.5 text-sm font-semibold" style={{ borderColor: "var(--a)" }}>✓ {i.msg}</div>)}
  </div>);
}

export function ChartCard({ title, sub, children, action }: any) {
  return (<div className="card p-4"><div className="mb-2 flex items-start justify-between gap-2">
    <div><h3 className="font-bold">{title}</h3>{sub && <p className="mut text-[13px] mt-0.5">{sub}</p>}</div>{action}</div>{children}</div>);
}

export function Loading({ label = "Loading live analytics…" }) {
  return <div className="card p-10 text-center mut"><Loader2 className="animate-spin inline mr-2" size={18} />{label}</div>;
}
export function ErrorBox({ error, retry }: any) {
  return (<div className="card p-6" role="alert"><div className="flex gap-2 items-center font-bold" style={{ color: "var(--bad)" }}><AlertTriangle size={17} /> Couldn't load this view</div>
    <p className="mut text-sm mt-1 break-words">{String(error)}</p>
    <p className="mut text-sm">Check the API is running: <code>.venv/bin/uvicorn api.main:app --port 8000</code></p>
    {retry && <button className="btn mt-3" onClick={retry}>↺ Retry</button>}</div>);
}
export function Empty({ label = "No data for the current selection." }) {
  return <div className="p-8 text-center mut"><Inbox className="inline mr-2" size={16} />{label}</div>;
}

export function DataTable({ rows, columns, pageSize = 10, onRow, searchKey }: any) {
  const [q, setQ] = useState(""); const [sort, setSort] = useState<{ k: string; dir: number } | null>(null); const [page, setPage] = useState(0);
  const filtered = useMemo(() => {
    let r = [...(rows || [])];
    if (q) r = r.filter((x: any) => JSON.stringify(x).toLowerCase().includes(q.toLowerCase()));
    if (sort) r.sort((a: any, b: any) => (a[sort.k] > b[sort.k] ? 1 : -1) * sort.dir);
    return r;
  }, [rows, q, sort]);
  const pages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const view = filtered.slice(page * pageSize, page * pageSize + pageSize);
  return (<div>
    <div className="mb-2 flex items-center gap-2"><input placeholder="🔎 Search table…" value={q} onChange={(e) => { setQ(e.target.value); setPage(0); }} style={{ minWidth: 220 }} />
      <span className="mut text-[13px]">{filtered.length} rows</span></div>
    <div style={{ overflowX: "auto" }}><table><thead><tr>{columns.map((c: any) => (
      <th key={c.k} onClick={() => setSort({ k: c.k, dir: sort?.k === c.k ? -sort.dir : 1 })} style={{ cursor: "pointer" }}>{c.label} {sort?.k === c.k ? (sort.dir > 0 ? "↑" : "↓") : ""}</th>))}</tr></thead>
      <tbody>{view.map((r: any, i: number) => (<tr key={i} onClick={() => onRow && onRow(r)} style={onRow ? { cursor: "pointer" } : {}}>
        {columns.map((c: any) => <td key={c.k}>{c.fmt ? c.fmt(r[c.k], r) : String(r[c.k] ?? "—")}</td>)}</tr>))}
        {!view.length && <tr><td colSpan={columns.length}><Empty /></td></tr>}</tbody></table></div>
    <div className="mt-2 flex items-center gap-2">
      <button className="btn" disabled={page === 0} onClick={() => setPage(page - 1)}>← Prev</button>
      <span className="mut text-[13px]">Page {page + 1} / {pages}</span>
      <button className="btn" disabled={page >= pages - 1} onClick={() => setPage(page + 1)}>Next →</button></div></div>);
}

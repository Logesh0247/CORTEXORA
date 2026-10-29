"use client";
import Link from "next/link";
import { useMemo, useState } from "react";
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

export function KpiCard({ label, value, delta, sub, href, title }: any) {
  const inner = (<>
    <div className="lab flex items-center gap-1.5">{label}{title && <span title={title}><Info size={12} /></span>}</div>
    <div className="mt-1 text-[24px] font-extrabold tracking-tight">{value}</div>
    <div className="mt-0.5 text-[13px] mut">
      {typeof delta === "number" && (<span style={{ color: delta >= 0 ? "var(--good)" : "var(--bad)", fontWeight: 800 }}>
        {delta >= 0 ? <ArrowUpRight size={13} className="inline" /> : <ArrowDownRight size={13} className="inline" />} {Math.abs(delta)}% </span>)}
      {sub}</div></>);
  const cls = "card card-hover p-4 block";
  return href ? <Link href={href} className={cls}>{inner}</Link> : <div className={cls}>{inner}</div>;
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

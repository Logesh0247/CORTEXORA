"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ChevronDown, Menu, Moon, Sun, Bell, Search, Command, X, Settings, FileText, LogOut, Sparkles } from "lucide-react";
import { NAV, ALL_ROUTES } from "@/lib/nav";
import Copilot from "./Copilot";
import { api } from "@/lib/api";
import { Toaster } from "./ui";

export function LogoMark({ size = 34 }: { size?: number }) {
  return (<svg width={size} height={size} viewBox="0 0 40 40" aria-hidden="true" style={{ flexShrink: 0 }}>
    <defs><linearGradient id="cxg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stopColor="#6366f1" /><stop offset="100%" stopColor="#8b7cf6" /></linearGradient></defs>
    <rect x="1.5" y="1.5" width="37" height="37" rx="11" fill="url(#cxg)" opacity=".16" />
    <rect x="1.5" y="1.5" width="37" height="37" rx="11" fill="none" stroke="url(#cxg)" strokeWidth="1.4" />
    <path d="M27.5 14.5A9.5 9.5 0 1 0 27.5 25.5" fill="none" stroke="url(#cxg)" strokeWidth="3.2" strokeLinecap="round" />
    <circle cx="28.6" cy="20" r="2.4" fill="#22b8d8" /><circle cx="14" cy="13.5" r="1.6" fill="#8b7cf6" opacity=".85" /><circle cx="12.5" cy="26" r="1.6" fill="#6366f1" opacity=".7" /></svg>);
}

export default function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname() || "/";
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [mobile, setMobile] = useState(false);
  const [dark, setDark] = useState(true);
  const [palette, setPalette] = useState(false);
  const [pq, setPq] = useState("");
  const [pending, setPending] = useState(0);
  const [pendingList, setPendingList] = useState<any[]>([]);
  const [notifOpen, setNotifOpen] = useState(false);
  const [profOpen, setProfOpen] = useState(false);
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({});
  const current = ALL_ROUTES.find((r) => r.href === path);
  const section = NAV.find((g) => g.items.some((i) => i.href === path))?.section || "";

  useEffect(() => {
    const saved = localStorage.getItem("cx-theme");
    const d = saved ? saved === "dark" : true;
    setDark(d); document.documentElement.classList.toggle("dark", d);
  }, []);
  useEffect(() => { api("/api/decisions").then((d) => { const px = (d.decisions || []).filter((x: any) => x.status === "pending"); setPending(px.length); setPendingList(px.slice(0, 5)); }).catch(() => {}); }, [path]);
  useEffect(() => { setNotifOpen(false); setProfOpen(false); }, [path]);
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setPalette(true); }
      if (e.key === "Escape") setPalette(false);
    };
    window.addEventListener("keydown", h); return () => window.removeEventListener("keydown", h);
  }, []);
  function toggleTheme() {
    const d = !dark; setDark(d);
    document.documentElement.classList.toggle("dark", d);
    localStorage.setItem("cx-theme", d ? "dark" : "light");
  }
  const results = useMemo(() => ALL_ROUTES.filter((r) => (r.label + r.desc).toLowerCase().includes(pq.toLowerCase())), [pq]);

  const sidebar = (
    <div className="flex flex-col gap-1 p-3" style={{ minHeight: "100%" }}>
      <Link href="/" className="flex items-center gap-2.5 px-1.5 py-2 no-underline" style={{ color: "var(--txt)" }} title="CORTEXORA — Home">
        <LogoMark size={36} />
        {!collapsed && (<span style={{ minWidth: 0 }}><span className="font-black tracking-[.14em] text-[15px]">CORTEXORA</span><br />
          <span className="mut" style={{ fontSize: 10, lineHeight: 1.3, display: "block" }}>The Intelligence Engine for<br />Predictive Business Decisions</span></span>)}
      </Link>
      {NAV.map((g) => (
        <div key={g.section}>
          <button className="lab w-full flex items-center justify-between px-2 pt-3.5 pb-1" style={{ background: "none", border: "none", cursor: "pointer" }}
            onClick={() => setOpenGroups((s) => ({ ...s, [g.section]: !(s[g.section] ?? true) }))}>
            {!collapsed && g.section}<ChevronDown size={13} style={{ transform: (openGroups[g.section] ?? true) ? "" : "rotate(-90deg)" }} /></button>
          {(openGroups[g.section] ?? true) && g.items.map((it) => (
            <Link key={it.href} href={it.href} title={collapsed ? `${it.label} — ${it.desc}` : undefined}
              className={`navlink ${path === it.href ? "active" : ""}`} onClick={() => setMobile(false)}>
              <it.icon size={17} style={{ flexShrink: 0 }} />
              {!collapsed && <span className="flex-1">{it.label}</span>}
              {!collapsed && (it as any).badge && pending > 0 && (
                <span style={{ background: "var(--bad)", color: "#fff", borderRadius: 999, fontSize: 11, fontWeight: 800, padding: "1px 7px" }}>{pending}</span>)}
            </Link>))}
        </div>))}
      <div className="mt-auto px-2 pt-4">
        {!collapsed && (<div className="card p-3 text-[12px]">
          <span className="status-dot pulse mr-1.5" style={{ background: "var(--good)", display: "inline-block" }} />
          <b>Demo Data</b><div className="mut mt-1">Synthetic dataset (seed=42). Figures are illustrative; calculations are real.</div></div>)}
        <button className="btn w-full mt-2 justify-center" onClick={() => setCollapsed(!collapsed)}>{collapsed ? "»" : "« Collapse"}</button>
      </div>
    </div>);

  return (<div className="gridbg" style={{ display: "flex", minHeight: "100vh" }}>
    <aside className="hidden lg:block" style={{ width: collapsed ? 74 : 256, flexShrink: 0, position: "sticky", top: 0, height: "100vh", overflowY: "auto", borderRight: "1px solid var(--line)", background: "var(--side)", transition: "width .18s" }}>{sidebar}</aside>
    {mobile && (<div style={{ position: "fixed", inset: 0, zIndex: 70, background: "rgba(2,6,16,.55)", backdropFilter: "blur(2px)" }} onClick={() => setMobile(false)}>
      <aside style={{ width: 264, height: "100%", background: "var(--side)", overflowY: "auto" }} onClick={(e) => e.stopPropagation()}>{sidebar}</aside></div>)}
    <div style={{ flex: 1, minWidth: 0 }}>
      <header className="flex items-center gap-2.5 px-4 lg:px-6 py-3 sticky top-0 z-40" style={{ background: "color-mix(in srgb, var(--bg) 82%, transparent)", backdropFilter: "blur(10px)", borderBottom: "1px solid var(--line)" }}>
        <button className="btn lg:hidden" aria-label="Open navigation" onClick={() => setMobile(true)}><Menu size={17} /></button>
        <div style={{ minWidth: 0 }}>
          <div className="text-[11px] mut font-bold tracking-wider">{section || "OVERVIEW"} <span className="mx-1">/</span> {current?.label || "Home"}</div>
          <div className="font-extrabold text-[17px] leading-tight truncate">{current?.label || "Home"}</div>
        </div>
        <div className="flex-1" />
        <button className="btn hidden md:inline-flex" onClick={() => setPalette(true)}><Search size={15} /> Search… <span className="kbd">Ctrl K</span></button>
        <select aria-label="Global period" defaultValue="10000" onChange={(e) => { localStorage.setItem("cx-days", e.target.value); window.dispatchEvent(new CustomEvent("cx-days", { detail: e.target.value })); }}
          title="Global period — updates the Home dashboard">
          <option value="30">Last 30 days</option><option value="90">Last 90 days</option><option value="182">Last 6 months</option><option value="365">Last year</option><option value="10000">All time</option></select>
        <span className="chip hidden md:inline-flex" style={{ cursor: "default" }} title="The connected dataset. Upload your own in Data Sources.">🗂️ Demo dataset</span>
        <div style={{ position: "relative" }}>
          <button className="btn" aria-label="Notifications" aria-haspopup="true" aria-expanded={notifOpen} title="Notifications" onClick={() => { setNotifOpen(!notifOpen); setProfOpen(false); }} style={{ position: "relative" }}>
            <Bell size={16} />{pending > 0 && <span style={{ position: "absolute", top: -6, right: -6, background: "var(--bad)", color: "#fff", borderRadius: 999, fontSize: 10, fontWeight: 800, padding: "0 5px" }}>{pending}</span>}</button>
          {notifOpen && (<div className="card p-2" role="menu" style={{ position: "absolute", right: 0, top: 44, width: "min(340px,88vw)", zIndex: 65 }}>
            <div className="px-2 py-1.5 flex items-center justify-between"><b className="text-sm">Notifications</b><span className="chip on" style={{ cursor: "default" }}>{pending} pending</span></div>
            {pendingList.length ? pendingList.map((d: any) => (
              <button key={d.recommendation_id} className="navlink w-full text-left" onClick={() => router.push("/decisions")}>
                <span className="status-dot" style={{ background: "var(--warn)" }} />
                <span style={{ minWidth: 0 }}><span className="block text-[13px] font-semibold truncate">{d.area} — action awaiting review</span>
                  <span className="block mut text-[12px] truncate">{d.problem}</span></span></button>))
              : <p className="mut text-sm px-2 py-2">All caught up — no pending decisions.</p>}
            <button className="btn w-full justify-center mt-1" onClick={() => router.push("/decisions")}>Open Decision Intelligence</button>
          </div>)}
        </div>
        <button className="btn primary" aria-label="Ask Copilot" onClick={() => window.dispatchEvent(new Event("cx-open-copilot"))}><Sparkles size={15} /> <span className="hidden md:inline">Copilot</span></button>
        <button className="btn" aria-label="Toggle theme" title={dark ? "Switch to light theme" : "Switch to dark theme"} onClick={toggleTheme}>{dark ? <Sun size={16} /> : <Moon size={16} />}</button>
        <div style={{ position: "relative" }}>
          <button className="btn" aria-label="Profile menu" aria-haspopup="true" aria-expanded={profOpen} onClick={() => { setProfOpen(!profOpen); setNotifOpen(false); }}
            style={{ width: 34, height: 34, padding: 0, justifyContent: "center", borderRadius: 999, background: "linear-gradient(135deg,var(--a),var(--a2))", color: "#fff", border: "none", fontWeight: 800, fontSize: 13 }}>CX</button>
          {profOpen && (<div className="card p-2" role="menu" style={{ position: "absolute", right: 0, top: 44, width: 230, zIndex: 65 }}>
            <div className="px-2 py-1.5"><div className="font-bold text-sm">CORTEXORA Workspace</div><div className="mut text-[12px]">Demo dataset · Analyst role</div></div>
            <button className="navlink w-full text-left" onClick={() => router.push("/settings")}><Settings size={15} /> Settings & preferences</button>
            <button className="navlink w-full text-left" onClick={() => router.push("/reports")}><FileText size={15} /> Reports</button>
            <button className="navlink w-full text-left" onClick={toggleTheme}>{dark ? <Sun size={15} /> : <Moon size={15} />} {dark ? "Light theme" : "Dark theme"}</button>
            <div className="mut text-[11.5px] px-2 py-1.5" style={{ borderTop: "1px solid var(--line)" }}><LogOut size={11} className="inline mr-1" />Sign-out is disabled in demo mode.</div>
          </div>)}
        </div>
      </header>
      <main className="px-4 lg:px-6 py-5" style={{ maxWidth: 1480, margin: "0 auto" }}><div key={path} className="page-enter">{children}</div></main>
      <Toaster />
      <footer className="px-6 pb-8 text-center text-[12px] mut">CORTEXORA · Predict the Future. Optimize the Present. Engineer Business Growth. · Demo data — calculations are real, figures illustrative.</footer>
    </div>
    <Copilot />
    {palette && (<div style={{ position: "fixed", inset: 0, zIndex: 80, background: "rgba(0,0,0,.55)", display: "flex", justifyContent: "center", paddingTop: "12vh" }} onClick={() => setPalette(false)}>
      <div className="card p-3" style={{ width: "min(560px,92vw)", height: "fit-content" }} onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Command palette">
        <div className="flex items-center gap-2"><Command size={16} /><input autoFocus value={pq} onChange={(e) => setPq(e.target.value)} placeholder="Go to a page, or search actions…" style={{ flex: 1 }} />
          <button className="btn" onClick={() => setPalette(false)}><X size={14} /></button></div>
        <div className="mt-2 space-y-1" style={{ maxHeight: 340, overflowY: "auto" }}>
          {results.map((r) => (<button key={r.href} className="navlink w-full text-left" onClick={() => { setPalette(false); router.push(r.href); }}>
            <r.icon size={16} /><span className="flex-1">{r.label}</span><span className="mut text-[12px]">{r.desc}</span></button>))}
          <button className="navlink w-full text-left" onClick={() => { setPalette(false); window.dispatchEvent(new Event("cx-open-copilot")); }}>🤖 Ask CORTEXORA Copilot<span className="mut text-[12px] ml-auto">AI assistant</span></button>
          {!results.length && <div className="mut text-sm p-2">No matches — try “forecast”, “churn” or “decision”.</div>}
        </div>
        <div className="mut text-[11px] mt-2">Shortcuts: <span className="kbd">Ctrl/⌘ K</span> palette · <span className="kbd">Esc</span> close</div>
      </div></div>)}
  </div>);
}

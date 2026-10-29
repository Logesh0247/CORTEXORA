"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PageHead, ChartCard } from "@/components/ui";
export default function Settings() {
  const [theme, setTheme] = useState("dark"); const [days, setDays] = useState("10000"); const [copilotCtx, setCopilotCtx] = useState(true);
  const [health, setHealth] = useState<any>(null); const [saved, setSaved] = useState("");
  useEffect(() => {
    setTheme(localStorage.getItem("cx-theme") || "dark"); setDays(localStorage.getItem("cx-days") || "10000");
    setCopilotCtx(localStorage.getItem("cx-copilot-ctx") !== "0");
    api("/api/health").then(setHealth).catch(() => setHealth({ status: "unreachable" }));
  }, []);
  function apply() {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem("cx-theme", theme); localStorage.setItem("cx-days", days);
    localStorage.setItem("cx-copilot-ctx", copilotCtx ? "1" : "0");
    window.dispatchEvent(new CustomEvent("cx-days", { detail: days }));
    setSaved("✅ Preferences saved on this device.");
  }
  return (<div>
    <PageHead title="Settings" question="System" desc="Only settings that actually work are shown. Preferences persist on this device." />
    <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(320px,1fr))" }}>
      <div className="card p-4"><h3 className="font-bold mb-3">🎨 Appearance & defaults</h3>
        <label className="lab">Theme</label>
        <select value={theme} onChange={(e) => setTheme(e.target.value)} className="w-full mb-3"><option value="dark">Dark (midnight)</option><option value="light">Light</option></select>
        <label className="lab">Default global period</label>
        <select value={days} onChange={(e) => setDays(e.target.value)} className="w-full mb-3">
          <option value="30">Last 30 days</option><option value="90">Last 90 days</option><option value="182">Last 6 months</option><option value="365">Last year</option><option value="10000">All time</option></select>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={copilotCtx} onChange={(e) => setCopilotCtx(e.target.checked)} style={{ width: "auto" }} /> Copilot may include current-page context</label>
        <button className="btn primary mt-4" onClick={apply}>Save preferences</button>
        {saved && <p className="text-sm mt-2" style={{ color: "var(--good)" }}>{saved}</p>}</div>
      <ChartCard title="🔌 Model & API configuration status" sub="No secrets are stored in, or exposed to, the frontend">
        <div className="text-sm space-y-2">
          <div>Analytics API (FastAPI): <b>{health ? (health.status === "ok" ? "✅ connected" : "⛔ " + health.status) : "checking…"}</b></div>
          <div>Data mode: <b>Demo Data</b> — synthetic dataset (seed=42){health?.records ? ` · ${health.records.toLocaleString()} records · through ${health.data_through}` : ""}</div>
          <div>CORTEXORA Copilot: <b>Deterministic demo mode</b> — data-grounded answers from validated analytics functions. No LLM API key is configured; when one is added server-side (env var, backend only), Copilot upgrades without any frontend change.</div>
          <div>Warehouse: SQLite (demo) · schema is Postgres-portable · decisions & pipeline logs survive reloads.</div></div></ChartCard>
      <ChartCard title="⌨️ Keyboard shortcuts" sub="Documented and typing-safe">
        <div className="text-sm space-y-1.5"><div><span className="kbd">Ctrl/⌘ K</span> Command palette — jump to any page or Copilot</div>
          <div><span className="kbd">Esc</span> Close palette / drawer</div>
          <div><span className="kbd">Tab</span> / <span className="kbd">Shift+Tab</span> Move through controls with visible focus</div></div></ChartCard>
    </div></div>);
}

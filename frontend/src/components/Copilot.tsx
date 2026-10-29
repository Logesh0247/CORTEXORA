"use client";
import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { Bot, X, Send, Plus, Copy, ThumbsUp, ThumbsDown, Sparkles } from "lucide-react";
import { api } from "@/lib/api";

const NAV_HREF: Record<string, string> = { "Demand Forecasting": "/forecasting", "Customer Intelligence": "/customers", "Marketing Intelligence": "/marketing", "Decision Intelligence": "/decisions", "Business Growth": "/growth", "Pricing & Profitability": "/pricing", "Data & Model Health": "/health", "Executive Intelligence": "/executive" };
const PAGE_PROMPTS: Record<string, string[]> = {
  "/forecasting": ["Forecast Electronics demand", "Which products may stock out?", "Can I trust this forecast?"],
  "/customers": ["Which customers are at churn risk?", "What is churn?", "Summarize the key insights."],
  "/marketing": ["Best marketing channel?", "How can we improve marketing efficiency?", "What is CAC?"],
  "/decisions": ["What should we prioritize today?", "What should we do next?", "Explain the largest change."],
  "/health": ["Can I trust this forecast?", "How much data do we have?", "What is PSI?"],
};
const askRef = { current: (_q: string) => {} };
const DEFAULT_PROMPTS = ["What is our revenue and profit?", "Why did revenue change?", "Find the biggest opportunity.", "What should we do next?"];

export default function Copilot() {
  const path = usePathname() || "/";
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [input, setInput] = useState("");
  const [includeCtx, setIncludeCtx] = useState(true);
  const [msgs, setMsgs] = useState<any[]>([
    { role: "assistant", text: "Hi, I'm **CORTEXORA Copilot** 🤖. Every answer is computed live from the warehouse by the Python analytics — I never invent numbers. (Demo mode: deterministic data-grounded assistant; no LLM API is configured.)", ts: new Date().toLocaleTimeString() }]);
  const boxRef = useRef<HTMLDivElement>(null);
  useEffect(() => { boxRef.current?.scrollTo(0, 1e7); }, [msgs, open]);
  useEffect(() => {
    const f = () => setOpen(true);
    const fq = (e: any) => { setOpen(true); if (e.detail) setTimeout(() => askRef.current(e.detail), 60); };
    window.addEventListener("cx-open-copilot", f); window.addEventListener("cx-ask-copilot", fq);
    return () => { window.removeEventListener("cx-open-copilot", f); window.removeEventListener("cx-ask-copilot", fq); };
  }, []);
  const prompts = PAGE_PROMPTS[path] || DEFAULT_PROMPTS;
  askRef.current = ask;
  async function ask(q: string) {
    if (!q.trim() || busy) return;
    setMsgs((m) => [...m, { role: "user", text: q, ts: new Date().toLocaleTimeString() }]);
    setInput(""); setBusy(true);
    try {
      const a = await api("/api/chat", { method: "POST", body: JSON.stringify({ question: q, page: includeCtx ? path : "" }) });
      setMsgs((m) => [...m, { role: "assistant", text: a.text, table: a.table, navigate: a.navigate, mode: a.mode, ts: new Date().toLocaleTimeString() }]);
    } catch (e: any) {
      setMsgs((m) => [...m, { role: "assistant", text: "⚠️ The assistant backend is unavailable right now. Start it with `.venv/bin/uvicorn api.main:app --port 8000`, then ask again.", ts: "" }]);
    } finally { setBusy(false); }
  }
  return (<>
    <button onClick={() => setOpen(!open)} aria-label="Open CORTEXORA Copilot"
      className="btn primary" style={{ position: "fixed", right: 20, bottom: 20, zIndex: 60, borderRadius: 999, padding: "12px 18px", boxShadow: "0 12px 30px rgba(2,80,160,.45)" }}>
      <Bot size={18} /> Copilot</button>
    {open && (<aside className="card" style={{ position: "fixed", right: 16, top: 70, bottom: 76, width: "min(400px,94vw)", zIndex: 59, display: "flex", flexDirection: "column", padding: 0, overflow: "hidden" }} aria-label="CORTEXORA Copilot">
      <div className="flex items-center justify-between px-4 py-3" style={{ borderBottom: "1px solid var(--line)" }}>
        <div className="font-extrabold flex items-center gap-2"><Sparkles size={16} style={{ color: "var(--a)" }} /> CORTEXORA Copilot</div>
        <div className="flex gap-1.5">
          <button className="btn" title="New conversation" onClick={() => setMsgs([msgs[0]])}><Plus size={15} /></button>
          <button className="btn" title="Close" onClick={() => setOpen(false)}><X size={15} /></button></div></div>
      <div className="px-3 pt-2.5 flex flex-wrap gap-1.5">
        {prompts.map((p) => <button key={p} className="chip" onClick={() => ask(p)}>{p}</button>)}
      </div>
      <label className="px-3 pt-2 text-[12px] mut flex items-center gap-1.5">
        <input type="checkbox" checked={includeCtx} onChange={(e) => setIncludeCtx(e.target.checked)} style={{ width: "auto" }} />
        Include current page context ({path})</label>
      <div ref={boxRef} className="px-3 py-3 space-y-2.5" style={{ overflowY: "auto", flex: 1 }}>
        {msgs.map((m, i) => (
          <div key={i} className={`p-3 rounded-xl text-[13.5px] leading-relaxed ${m.role === "user" ? "msg-me ml-8" : "msg-bot mr-4"}`}>
            <div style={{ whiteSpace: "pre-wrap" }}>{m.text}</div>
            {m.table?.length > 0 && (<div style={{ overflowX: "auto", marginTop: 8 }}><table>
              <thead><tr>{Object.keys(m.table[0]).map((k) => <th key={k}>{k}</th>)}</tr></thead>
              <tbody>{m.table.map((r: any, j: number) => <tr key={j}>{Object.values(r).map((v: any, k: number) => <td key={k}>{v}</td>)}</tr>)}</tbody></table></div>)}
            <div className="flex items-center gap-2 mt-1.5" style={{ opacity: .75, fontSize: 11 }}>
              <span>{m.ts}</span>
              {m.role === "assistant" && (<>
                <button title="Copy response" onClick={() => navigator.clipboard?.writeText(m.text)}><Copy size={12} /></button>
                <button title="Helpful"><ThumbsUp size={12} /></button><button title="Not helpful"><ThumbsDown size={12} /></button>
                {m.mode && <span>· {m.mode}</span>}</>)}
            </div></div>))}
        {busy && <div className="msg-bot p-3 text-sm mut mr-4" role="status"><span className="tdot" /> <span className="tdot" /> <span className="tdot" /> <span className="ml-1.5">Computing from the warehouse…</span></div>}
      </div>
      <div className="flex gap-2 p-3" style={{ borderTop: "1px solid var(--line)" }}>
        <input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && ask(input)}
          placeholder="Ask about your business…" style={{ flex: 1 }} aria-label="Ask CORTEXORA Copilot" />
        <button className="btn primary" onClick={() => ask(input)} disabled={busy}><Send size={15} /></button></div>
    </aside>)}
  </>);
}

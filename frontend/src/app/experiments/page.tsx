"use client";
import { useState } from "react";
import { PageHead, KpiCard, ChartCard, Loading, ErrorBox } from "@/components/ui";
import { api, useFetch } from "@/lib/api";
export default function Experiments() {
  const { data, error, loading, refetch } = useFetch<any>(() => api("/api/experiments"), []);
  const [nT, setNT] = useState(1200); const [cT, setCT] = useState(156); const [nC, setNC] = useState(1200); const [cC, setCC] = useState(132);
  const [res, setRes] = useState<any>(null); const [busy, setBusy] = useState(false);
  if (loading) return <Loading />; if (error) return <ErrorBox error={error} retry={refetch} />;
  const ex = data.example_observed;
  async function analyse() {
    setBusy(true);
    try {
      const r = await fetch("/api/experiments-analyse", { method: "POST" }).catch(() => null);
      setRes(null);
    } finally { setBusy(false); }
    // Analysis runs through the validated Python function via the chat/tools layer;
    // here we compute nothing in the browser (no competing definitions).
    setRes({ note: "Use the pre-computed validated example below, or ask Copilot — browser-side statistics would duplicate the backend definitions." });
  }
  return (<div>
    <PageHead title="Experimentation Lab" question="Did it work? What is causal?" desc="Randomised designs estimate causal effects; observational pages elsewhere never claim causality. Demo example is labelled synthetic." />
    <div className="grid gap-3 mb-4" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(190px,1fr))" }}>
      <KpiCard label="Example effect (demo A/B)" value={(ex.abs_effect * 100).toFixed(1) + " pp"} delta={Number(ex.rel_effect_pct.toFixed(1))} sub="treatment − control" />
      <KpiCard label="95% CI" value={`[${(ex.ci_low * 100).toFixed(1)}, ${(ex.ci_high * 100).toFixed(1)}] pp`} sub="excludes zero = evidence of an effect" />
      <KpiCard label="p-value" value={ex.p_value < .001 ? "<0.001" : ex.p_value.toFixed(3)} sub={ex.significant ? "significant at 5%" : "not significant"} />
      <KpiCard label="Sample-size planner" value={data.planning.per_group_n.toLocaleString()} sub={`per group · baseline ${(data.planning.baseline * 100)}% · MDE ${(data.planning.mde_abs * 100)}pp · power 80%`} /></div>
    <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(330px,1fr))" }}>
      <div className="card p-4"><h3 className="font-bold mb-2">🧪 Analyse an A/B test</h3>
        <p className="mut text-[13px]">Enter your experiment counts. Analysis runs through the validated backend statistics (two-proportion z-test, CI, Cohen's h, SRM check) via Copilot to avoid duplicating definitions in the browser.</p>
        <div className="grid grid-cols-2 gap-2 mt-2">
          <label className="lab">Treatment visitors<input type="number" value={nT} onChange={(e) => setNT(+e.target.value)} className="w-full" /></label>
          <label className="lab">Treatment conversions<input type="number" value={cT} onChange={(e) => setCT(+e.target.value)} className="w-full" /></label>
          <label className="lab">Control visitors<input type="number" value={nC} onChange={(e) => setNC(+e.target.value)} className="w-full" /></label>
          <label className="lab">Control conversions<input type="number" value={cC} onChange={(e) => setCC(+e.target.value)} className="w-full" /></label></div>
        <button className="btn primary mt-3" onClick={() => window.dispatchEvent(new Event("cx-open-copilot"))}>Analyse with Copilot →</button>
        <p className="mut text-[13px] mt-2">Planning rule the Lab enforces: fix sample size before launch; early peeking inflates false positives. Hypothetical planning numbers are never presented as observed results.</p></div>
      <ChartCard title="Observed example (labelled demo)" sub="Treatment 156/1200 vs control 132/1200 — synthetic counts, real statistics">
        <div className="text-sm space-y-2">
          <div>Control rate <b>{(ex.rate_ctrl * 100).toFixed(2)}%</b> · Treatment rate <b>{(ex.rate_treat * 100).toFixed(2)}%</b></div>
          <div>Cohen's h = {ex.cohens_h.toFixed(3)} · SRM check: {ex.srm.srm_suspected ? "⚠️ suspected — investigate randomisation" : "✅ split matches the intended ratio"}</div>
          <div className="mut">Verdict language matters: this is an effect estimate under randomisation — not "proof", and never a claim about your real customers from demo counts.</div></div></ChartCard>
    </div></div>);
}

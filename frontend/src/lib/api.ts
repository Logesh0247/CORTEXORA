"use client";
import { useEffect, useState, useCallback } from "react";
export const api = async (path: string, init?: RequestInit) => {
  const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...init });
  if (!r.ok) throw new Error((await r.text()).slice(0, 300) || `API ${r.status}`);
  return r.json();
};
export const money = (v: number) => "$" + Math.round(v ?? 0).toLocaleString();
export const pct = (v: number, d = 1) => `${((v ?? 0) * 100).toFixed(d)}%`;
export function useFetch<T>(fn: () => Promise<T>, deps: any[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const run = useCallback(() => {
    setLoading(true);
    return fn().then((d) => { setData(d); setError(""); }).catch((e) => setError(String(e.message || e))).finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  useEffect(() => { run(); }, [run]);
  return { data, error, loading, refetch: run };
}

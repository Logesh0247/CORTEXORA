"""Drift & model-performance monitoring (Phase 8).

Three different things — never conflated in the UI:
  1. Data drift: input feature distributions changed (PSI below).
  2. Prediction drift: the model's output distribution changed.
  3. Performance degradation: measured accuracy on *labelled, later* data fell.
Drift (1/2) does NOT imply degradation (3): a model can stay accurate on
shifted data, and can degrade with no obvious drift. Only (3) is evidence
about accuracy, and it requires ground-truth labels from a later period.
See docs/10_PHASE8_MONITORING.md.
"""
from __future__ import annotations
import numpy as np, pandas as pd

def population_stability_index(reference, current, bins: int = 10) -> float:
    """PSI of `current` vs `reference`, binned on reference quantiles.
    ~0 = identical distributions; larger = more shift."""
    ref, cur = np.asarray(reference, float), np.asarray(current, float)
    ref, cur = ref[~np.isnan(ref)], cur[~np.isnan(cur)]
    if len(ref) < 20 or len(cur) < 20: return float("nan")
    edges = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)))
    if len(edges) < 3: return float("nan")
    edges[0], edges[-1] = -np.inf, np.inf
    r_pct = np.histogram(ref, edges)[0] / len(ref)
    c_pct = np.histogram(cur, edges)[0] / len(cur)
    eps = 1e-4  # smoothing: empty bins must not explode the log ratio
    r_pct, c_pct = np.clip(r_pct, eps, None), np.clip(c_pct, eps, None)
    return float(np.sum((c_pct - r_pct) * np.log(c_pct / r_pct)))

def interpret_psi(psi: float) -> str:
    if pd.isna(psi): return "insufficient data"
    if psi < 0.10: return "stable"
    if psi < 0.25: return "moderate shift — watch"
    return "significant shift — investigate"

def drift_report(reference: pd.DataFrame, current: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    rows = []
    for c in columns:
        if c in reference and c in current:
            psi = population_stability_index(reference[c], current[c])
            rows.append(dict(feature=c, psi=round(psi, 4) if not pd.isna(psi) else np.nan,
                             status=interpret_psi(psi),
                             reference_mean=float(reference[c].mean()), current_mean=float(current[c].mean())))
    return pd.DataFrame(rows).sort_values("psi", ascending=False)

def performance_comparison(reference_metrics: dict, current_metrics: dict,
                           metric: str = "pr_auc", degradation_threshold: float = 0.05) -> dict:
    """Compare labelled-period performance. degradation = drop > threshold (absolute)."""
    ref, cur = reference_metrics.get(metric), current_metrics.get(metric)
    if ref is None or cur is None or pd.isna(ref) or pd.isna(cur):
        return dict(metric=metric, reference=ref, current=cur, delta=None, degraded=None,
                    note="Performance can only be assessed when labelled outcomes for the later period exist.")
    delta = float(cur - ref)
    return dict(metric=metric, reference=float(ref), current=float(cur), delta=delta,
                degraded=bool(delta < -degradation_threshold),
                note=("Measured performance fell beyond the threshold on later labelled data — investigate/retrain."
                      if delta < -degradation_threshold else
                      "No degradation beyond threshold on later labelled data. (Drift alone would not prove otherwise.)"))

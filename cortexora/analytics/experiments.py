"""Causal Inference & Experimentation Lab (Phase 6).

Methods here estimate *causal* effects only under their stated designs:
  - A/B tests: randomisation is the user's responsibility; we verify balance
    (SRM check), estimate the effect, and quantify uncertainty.
  - Difference-in-differences: valid only if parallel-trends is plausible —
    we surface the pre-period trend gap so the user must confront it.
Nothing in this module turns observational correlation into a causal claim.
See docs/08_PHASE6_ADVANCED_ANALYTICS.md.
"""
from __future__ import annotations
import numpy as np, pandas as pd
from scipy import stats

def ab_conversion(n_treat: int, conv_treat: int, n_ctrl: int, conv_ctrl: int, alpha: float = 0.05) -> dict:
    """Two-proportion z-test. Returns rates, absolute/relative effect, 95% CI, p-value, Cohen's h."""
    if min(n_treat, n_ctrl) <= 0 or not (0 <= conv_treat <= n_treat and 0 <= conv_ctrl <= n_ctrl):
        raise ValueError("Counts must satisfy 0 <= conversions <= n, with n > 0 in both groups.")
    pt, pc = conv_treat / n_treat, conv_ctrl / n_ctrl
    diff = pt - pc
    pooled = (conv_treat + conv_ctrl) / (n_treat + n_ctrl)
    se_pooled = np.sqrt(pooled * (1 - pooled) * (1 / n_treat + 1 / n_ctrl))
    z = diff / se_pooled if se_pooled else 0.0
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    se = np.sqrt(pt * (1 - pt) / n_treat + pc * (1 - pc) / n_ctrl)  # unpooled, for the CI
    crit = stats.norm.ppf(1 - alpha / 2)
    h = 2 * np.arcsin(np.sqrt(pt)) - 2 * np.arcsin(np.sqrt(pc))
    return dict(rate_treat=pt, rate_ctrl=pc, abs_effect=diff,
                rel_effect_pct=(diff / pc * 100) if pc else float("nan"),
                ci_low=diff - crit * se, ci_high=diff + crit * se, z=float(z), p_value=float(p),
                cohens_h=float(h), significant=bool(p < alpha), alpha=alpha)

def ab_continuous(treat: np.ndarray, ctrl: np.ndarray, alpha: float = 0.05) -> dict:
    """Welch's t-test for a continuous outcome (e.g. revenue per user)."""
    t, c = np.asarray(treat, float), np.asarray(ctrl, float)
    res = stats.ttest_ind(t, c, equal_var=False)
    diff = t.mean() - c.mean()
    se = np.sqrt(t.var(ddof=1) / len(t) + c.var(ddof=1) / len(c))
    crit = stats.norm.ppf(1 - alpha / 2)
    sd = np.sqrt((t.var(ddof=1) + c.var(ddof=1)) / 2)
    return dict(mean_treat=float(t.mean()), mean_ctrl=float(c.mean()), abs_effect=float(diff),
                ci_low=float(diff - crit * se), ci_high=float(diff + crit * se),
                p_value=float(res.pvalue), cohens_d=float(diff / sd) if sd else 0.0,
                significant=bool(res.pvalue < alpha), alpha=alpha)

def required_sample_size(baseline_rate: float, mde_abs: float, alpha: float = 0.05, power: float = 0.8) -> int:
    """Per-group n to detect an absolute lift `mde_abs` over `baseline_rate` (two-sided)."""
    if not (0 < baseline_rate < 1 and 0 < baseline_rate + mde_abs < 1 and mde_abs != 0):
        raise ValueError("Need 0 < baseline < 1 and baseline+MDE inside (0,1).")
    za, zb = stats.norm.ppf(1 - alpha / 2), stats.norm.ppf(power)
    p1, p2 = baseline_rate, baseline_rate + mde_abs
    n = (za + zb) ** 2 * (p1 * (1 - p1) + p2 * (1 - p2)) / mde_abs ** 2
    return int(np.ceil(n))

def srm_check(n_treat: int, n_ctrl: int, expected_treat_share: float = 0.5) -> dict:
    """Sample-ratio-mismatch check: chi-square of observed split vs intended split.
    A failed SRM means randomisation likely broke — do not trust the experiment."""
    total = n_treat + n_ctrl
    exp = np.array([total * expected_treat_share, total * (1 - expected_treat_share)])
    chi2, p = stats.chisquare([n_treat, n_ctrl], exp)
    return dict(observed_share=n_treat / total, expected_share=expected_treat_share,
                chi2=float(chi2), p_value=float(p), srm_suspected=bool(p < 0.001))

def diff_in_diff(df: pd.DataFrame, outcome: str = "y", treated: str = "treated", post: str = "post") -> dict:
    """2x2 DiD via OLS y ~ treated + post + treated:post (HC1 robust SEs).
    Also reports the pre-period mean gap so parallel-trends can be eyeballed."""
    import statsmodels.formula.api as smf
    d = df.copy(); d[treated] = d[treated].astype(int); d[post] = d[post].astype(int)
    fit = smf.ols(f"{outcome} ~ {treated} * {post}", data=d).fit(cov_type="HC1")
    key = f"{treated}:{post}"
    pre = d[d[post] == 0].groupby(treated)[outcome].mean()
    return dict(did_effect=float(fit.params[key]), ci_low=float(fit.conf_int().loc[key, 0]),
                ci_high=float(fit.conf_int().loc[key, 1]), p_value=float(fit.pvalues[key]),
                pre_period_gap=float(pre.get(1, np.nan) - pre.get(0, np.nan)), n=int(len(d)),
                caveat="Causal only if treated/control would have trended in parallel without the intervention.")

def mmm_readiness(mkt: pd.DataFrame, has_revenue_outcome: bool = False) -> pd.DataFrame:
    """Gate for Marketing Mix Modelling. MMM is NOT fitted unless checks pass —
    an unidentifiable model presented confidently is worse than no model."""
    weeks = mkt.spend_date.nunique() if "spend_date" in mkt else 0
    chans = mkt.channel.nunique() if "channel" in mkt else 0
    cv = mkt.groupby("channel").spend.std().div(mkt.groupby("channel").spend.mean()).min() if chans else 0
    checks = [
        ("≥52 weekly observations", weeks >= 52, f"{weeks} weeks"),
        ("≥3 channels with spend", chans >= 3, f"{chans} channels"),
        ("Spend varies over time (min channel CV > 0.10)", bool(cv > 0.10), f"min CV = {cv:.2f}"),
        ("Revenue outcome joinable to spend by week", has_revenue_outcome,
         "available" if has_revenue_outcome else "MISSING — orders are not attributed to marketing weeks/channels"),
        ("External controls (price, seasonality, promos)", False, "not in dataset — omitted-variable risk"),
    ]
    return pd.DataFrame(checks, columns=["Requirement", "Met", "Evidence"])

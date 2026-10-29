# Phase 6 — Advanced Analytics: what's real, what's gated, and why

## Experiments & Causal Lab (implemented, tested)
- **A/B conversion analyser:** two-proportion z-test, absolute + relative effect, 95% CI (unpooled SE), Cohen's h, SRM (sample-ratio-mismatch) check — a failed SRM warns that randomisation likely broke.
- **Continuous outcomes:** Welch's t-test + Cohen's d (`ab_continuous`).
- **Design guidance:** per-group sample size for a stated baseline/MDE (α=.05, power=.80). Fixed *before* launch; early peeking invalidates p-values.
- **Difference-in-differences:** OLS interaction with HC1 robust SEs; pre-period gap surfaced. Causal only under parallel trends — stated in every output. Demo data is synthetic with a known +8 effect so recovery is verifiable (unit test asserts it).
Language rule: results are "effect estimates under this design", never "proof". Correlation tools elsewhere in CORTEXORA (discount buckets, response curves) remain labelled non-causal.

## Marketing Mix Modelling (gated — deliberately NOT fitted)
Readiness checklist on the Marketing page: ≥52 weekly obs ✓ (103), ≥3 channels ✓, spend variation ✓, **revenue outcome joinable to spend ✗**, **external controls ✗**. Without a marketing-linked revenue outcome and controls, an MMM would attribute order revenue (generated independently of spend in the synthetic data, and unattributed in real exports) to channels essentially arbitrarily. When real weekly revenue-by-channel + price/promo controls exist, fit a ridge/Bayesian MMM with adstock here and report posterior intervals — until then the gated message *is* the correct product behaviour.

## Competitor Intelligence (implemented via user snapshots)
No live feed exists, and none is simulated. Users upload compliantly collected public-price snapshots (product_id, competitor, price, observed_at, source_url); schema is strictly validated, gaps vs our list price computed, ≥5% undercuts alerted, reports downloadable. Example data is derived from our own list prices and labelled illustrative.

## Next gate (Phase 7+)
Use the Lab prospectively: e.g. turn the Decision Engine's discount-policy recommendation into a designed A/B test, then record expected-vs-actual in `decisions` (outcome tracking).

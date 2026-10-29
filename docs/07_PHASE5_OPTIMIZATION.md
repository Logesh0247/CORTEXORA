# Phase 5 — Business Optimization: methods & assumptions

## Inventory reorder (forecast-based)
Target stock = forecast_daily × (lead_time + 30d review) + safety stock; safety = 1.65 × σ_daily × √lead (≈95% cycle service level, normal-demand assumption). Reorder qty = max(target − on-hand, 0). Expected stockout units = max(forecast×lead − on-hand, 0). Costs = qty × unit_cost. These are scenario calculations from the demand forecast — accuracy inherits forecast error (see Forecasting page WAPE).

## Discount effectiveness
Revenue/profit/margin by discount bucket (0/5/10/20%+). **Observed association only** — discounted items differ systematically; no causal claim. A causal answer needs an experiment (Phase 6).

## Marketing budget allocation
Per channel, fit log(conversions)=log(a)+b·log(spend) on weekly data (power response curve; b<1 = diminishing returns). Channels with R²≤0.3 or implausible b are marked unreliable and excluded — with a visible note, not silently used. Allocation maximises Σ a_c·spend_c^b_c subject to Σ spend = budget and each channel ≤60% of budget (SciPy SLSQP). On the synthetic generator the true a/b are known by construction, so recovery can be checked; on real data these are associational estimates, **not** incremental/cross-channel causal effects (that is MMM/causal territory, Phase 6, gated on data).

## Pricing
Break-even units = fixed cost / (price − unit cost); infinite when contribution ≤0. Price simulator remains assumption-based (user-supplied elasticity).

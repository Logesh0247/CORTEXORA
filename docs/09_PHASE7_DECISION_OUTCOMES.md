# Phase 7 — Decision Intelligence completion: outcome tracking

## Lifecycle (enforced in code, not just drawn)
`pending → approved / rejected / deferred → measured`
- **Approve/reject/defer** stamps `decided_at` and an optional decision owner.
- Each area has a default **measurement period** (Inventory 30d, Marketing 28d, Pricing 28d, Customer 90d); the page shows the outcome due date.
- **Record outcome** (`record_outcome`) is refused unless the decision is `approved` — you cannot "evaluate" an action never taken. A measurement note (source/period/caveats) is mandatory in the UI. Recording moves the decision to terminal status `measured`.
- Old databases are migrated in place (`ensure_decision_schema`, tested) — no data loss, audit history preserved.

## Did our decision work?
`outcome_summary` compares actual vs expected for measured decisions: mean/median variance %, share within ±20%, and per-area bias. Interpretation rule shown in the UI: persistent bias in one area means that detector's impact assumptions are mis-calibrated → adjust the detector, rather than reacting to a single result.

## Honesty constraints
CORTEXORA ships with **zero prefilled outcomes** — an actual outcome exists only when a human records one with its measurement note. The Pricing recommendation explicitly routes to the Experiments & Causal Lab first, so its outcome can be causal rather than anecdotal.

## Remaining for full closure
Automatic outcome measurement (recomputing e.g. inventory shortfall from new data after the period elapses) requires fresh post-decision data feeds; on a static demo dataset it would be theatre, so it is left as a documented extension point (`record_outcome` is the single entry point an automated measurer would call).

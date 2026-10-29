# Dataset Strategy

## Current: clearly-labelled synthetic data (v1 development)
`cortexora/data/generate_sample.py`, seed=42, 24 months of retail transactions. Generated, **never presented as real**. Every UI page using it shows a "Synthetic demo data" banner. Why synthetic first: no licensed dataset was present in the repo, pipeline/metric correctness must be provable against known ground truth.

## Target real datasets (when introduced, record source+license in data lineage)
- UCI Online Retail II (CC BY 4.0) — transactions/RFM/forecasting. Requires cleaning (returns, missing CustomerID).
- Olist Brazilian E-Commerce (CC BY-NC-SA 4.0) — orders/customers/geography; NC clause limits commercial use.
- Marketing spend: no credible public weekly channel dataset — keep synthetic or user upload; MMM blocked until ≥52 weeks real data.
Rules: raw files immutable in data/raw/, source URL + license + retrieval date logged in `docs/DATA_LINEAGE.md` (create when first real dataset lands), PII minimised/hashed.

## Upload path (future): schema-validated CSV upload reusing pipelines.validation — invalid schema rejected with explicit errors.

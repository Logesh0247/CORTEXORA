# Upload & Analyse Your Dataset

**Where:** Streamlit app → sidebar **OVERVIEW → 📥 Upload & Analyse Data**.

**How it works**
1. Upload one transactional CSV (one row per sold item is ideal; a downloadable template shows the perfect format).
2. CORTEXORA auto-detects columns from common synonyms (InvoiceNo, Quantity, Price, Description, Country…) — you confirm or change every mapping. Required: date, product, quantity, unit price.
3. Click **Analyse my dataset**: rows that fail parsing are dropped *and counted in front of you*; negative quantities are treated as returns; if there's no cost column, profit/margin uses your chosen cost-ratio assumption and is labelled an estimate everywhere it appears.
4. You immediately get: KPI cards, trend (metric × daily/weekly/monthly), category/region/channel segments, top products & customers, and a category forecast with hold-out WAPE vs baseline (only when ≥24 weekly periods exist — otherwise it says why not).
5. Optionally download the cleaned CORTEXORA-format tables, or **load the dataset as the live warehouse** (replaces the demo data; decision audit history is preserved). Uploaded inventory stock is unknown (=0) and marketing modules stay inactive until spend data exists — stated on the page, not hidden.

Implementation: `cortexora/pipelines/upload.py` (mapping/transform, unit-tested incl. UCI-style files) + the app page. The transform output matches `database/schema.sql` exactly, so the existing ETL quality gate validates it on load.

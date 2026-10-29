# AI Assistant (Phase 11)

**What it is:** a data-grounded chat assistant (`cortexora/assistant/chatbot.py`) with a Streamlit chat UI (page: **AI Assistant**). It answers business questions by calling the same analytics the dashboards use — metrics layer, forecasting, churn artifact, reorder plan, marketing optimiser, decision log — and renders supporting tables plus a button to the module behind the answer.

**What it is not:** it does not call an external LLM API. There is no API key in this deployment, sending warehouse data to a third-party model would be a privacy decision for the owner, and an LLM improvising numbers would violate CORTEXORA's honesty rules. The assistant is transparent NLU/routing over real computations: intent detection → the relevant module function → an answer composed from its actual output. When a question can't be mapped to a computation, it says so and offers answerable examples (tested).

**Coverage:** headline KPIs + period deltas, why-did-revenue-change decomposition, top category/product/region/channel, category demand forecasts with measured WAPE vs baseline, churn segments + model metrics, stockout/reorder risk, marketing CAC + budget-optimiser estimate, pricing scenarios (elasticity assumption stated), decision pipeline status + top pending recommendation, data facts/freshness, metric definitions, and module navigation.

**Swapping in an LLM later:** keep `answer_question` as the tool layer — have the LLM call these same functions and quote only their outputs. Never let a language model free-generate business figures.

# CV and interview guide

## Recommended two-bullet CV entry

**Commerce Intelligence — Python, DuckDB SQL, Power BI**

- Developed an AI-assisted e-commerce analytics portfolio modelling 99,441 orders; reconciled order-level values independently and validated Power BI results across 565 month/state segments.
- Built a two-page delivery and customer-experience report; investigated an 81.0% March on-time rate versus 94.2% in other core months and defined evidence-based operational pilot proposals.

Use these statements only after personally understanding and demonstrating the work. They describe a portfolio artifact, not independently hand-coded production work or measured business improvements.

## Supported technical skills

**SQL:** CTEs, window functions, conditional aggregation, relational grain, date logic, fixed-precision currency, integrity checks and reproducible DuckDB transformations. **Python:** CSV/ZIP ingestion, SHA-256 source verification, Decimal/datetime reconciliation, statistical sensitivity checks and regression tests. **Power BI:** Import modelling, one-direction relationships, explicit DAX, filter context, synchronized slicers, conditional subtitles, PBIP/PBIR/TMDL and Desktop validation. **Analytics:** cohort comparison, rate-versus-volume prioritization, response-selection bias and bounded pilot recommendations.

Do not claim Fabric implementation, production orchestration, paid cloud deployment, causal inference, machine learning, pandas-based transformations or measured ROI. Those are not implemented here.

## A 30-second recruiter explanation

“I built an AI-assisted analytics portfolio to investigate delivery promises and customer experience in real marketplace data. It combines reproducible Python and SQL with a working two-page Power BI report. The key engineering challenge was avoiding duplicated amounts when joining orders to multiple items, payments and reviews. I also checked the headline findings independently: March's on-time rate was 81%, and survey timing creates a strong selection bias. The project includes validation evidence and practical investigation proposals, with no invented savings.”

## Five-minute technical walkthrough

**0:00–0:45 — Business decision and scope.** Explain the three questions: which purchase cohorts miss promises, where late volume/rates concentrate, and how review timing affects interpretation. This is historical Olist data, with Jan 2017–Aug 2018 as the core period. The 93.2% baseline is 89,672 on-time outcomes divided by 96,203 eligible delivered orders; it is not the proportion of all placed orders delivered on time.

**0:45–1:45 — Grain and model.** Open sql/02_marts.sql. Show the separate item/payment/review CTEs aggregated before the order join. Use a two-item, two-payment order to explain a naive four-row fan-out. Explain the separate item fact, unique keys and seven one-direction relationships. Multi-seller orders remain in overall KPIs but are not blamed on individual sellers. Stage is disconnected presentation metadata, not fabricated event data.

**1:45–2:45 — Definitions and proof.** On time compares calendar dates. Full-timestamp comparison would classify 7,826 source orders late instead of 6,534. Explain latest-review selection and null monetary values. Show the SQL checks, independent CSV/Decimal validator, fresh database hashes and actual Desktop DAX reconciliation. Mutation tests prove that a null lateness flag and missing result scopes fail instead of generating a false PASS. Schema validity is separate from real rendering/refresh.

**2:45–3:45 — Demonstrate the dashboard.** Start with All slicers. Choose March 2018: 7,003 eligible, 81.0% on time, 13.4 median days and 3.75 average selected review. Select RJ in the chart: 864 eligible, 65.5% on time. Clear the selection, then select RJ in the slicer and switch pages to demonstrate synchronization. Discuss the eight-row investigation queue using both denominator and rate. Explain the dynamic post-delivery coverage warning and the valid samples beside stage medians.

**3:45–4:30 — Explain the difficult finding.** March versus the other core months has a 13.1 percentage-point gap; state-standardized rates remain about 80.8% versus 94.2%. Eligibility is about 97.1% in both groups. That makes it a useful descriptive investigation signal, not an identified logistics cause. The month was selected after looking at the data. Post-delivery reviews cover only 29.2% of late versus 99.3% of on-time eligible orders, so even a post-delivery rating comparison is strongly selected.

**4:30–5:00 — Action and boundaries.** Propose a narrow RJ/cohort investigation, followed by a pilot with a comparable control cohort. Track calendar-date on-time rate and P90; guard against cancellations or simply lengthening promises. Ask for carrier event history, promise revisions, actual costs and returns before recommending a specific logistics change or estimating savings. Mention the source licence and local-only deployment.

## Five concepts you must personally understand

1. **Grain and fan-out.** Given two items and two payments, calculate what a direct join does to item prices. Explain how pre-aggregation and independent totals prevent it.
2. **Eligibility and denominators.** Recalculate 89,672 / 96,203 and 5,675 / 7,003. Explain excluded statuses, missing delivery dates, calendar-date logic and why purchase month differs from delivery month.
3. **DAX filter context.** Explain how State → Order filtering changes cards; why Product filters Item only; and why a score-segment tooltip must remove the score filter before computing the full band's low-rating share.
4. **Selection versus causation.** Explain why excluding pre-delivery responses does not create a representative late-order sample. A large descriptive difference or narrow interval does not identify a causal effect.
5. **Reproducibility versus proof.** Source hashes fix input identity, SQL tests enforce contracts, independent code checks calculations, and actual Desktop tests establish refresh/rendering. None alone proves production reliability or business impact.

## Honest AI-assistance disclosure

“AI assisted with code, report definitions, tests and documentation. I directed the scope and have personally reviewed [name the parts you actually reviewed]. I can explain [demonstrate the SQL grain, a DAX measure and a verified result].”

Replace the bracketed statements with your own completed review; do not recite them as facts before doing it. Before using the project in interviews, rerun the pipeline, inspect one raw order with multiple children, manually recalculate one month/state slice, explain the rating-selection caveat, and practice the five-minute demonstration without assistance.

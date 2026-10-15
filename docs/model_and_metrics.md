# Model, SQL and business logic

## Grain and joins

`raw` preserves all nine CSV schemas as text. `stg`/`core` type timestamps, integer keys and `DECIMAL(18,2)` money. SQL transformations run in a transaction; marts receive primary keys and relationship integrity is tested explicitly. Physical foreign-key constraints are not declared.

`mart.fact_order` has one row per source order (99,441). Item, payment and review collections are independently grouped by order before joining the header. Joining those detail tables directly would multiply amounts. `mart.fact_item` has one row per `(order_id, item_number)` (112,650); review identity is `(review_id, order_id)`, not `review_id` alone.

Power BI loads nine CSV tables:

| Table | Grain / key | Filter relationship |
|---|---|---|
| Order | One order / Order ID | Receives Date, State, Seller, Category, Status |
| Item | One order line / Order ID + Item Number | Receives Order and Product |
| Date | One calendar date / Date Key | Date → Order, purchase date |
| State | One customer state / State Key | State → Order |
| Seller | Seller plus multi/no-item buckets / Seller Key | Seller → Order |
| Category | Category plus multi/no-item buckets / Category Key | Category → Order |
| Product | One product / Product ID | Product → Item |
| Status | One status / Order Status | Status → Order |
| Stage | Three named process stages | Disconnected; measure chooses stage calculation |

All seven relationships are one-to-many and filter in one direction. Product filters item measures only; there is no product slicer that falsely implies filtering order KPIs. Seller/category order attributes are single-valued only when the order has exactly one seller/category. Multi-seller/category orders remain in overall KPIs but are excluded from the corresponding diagnostic queue. Customer identity is retained at order level; customer_id is an order-specific identifier, whereas customer_unique_id identifies returning customers.

See [model diagram](semantic_model.mmd). The exact exported column names, types and row counts are in `reports/validation/build_manifest.json`; all 36 DAX measures, formats and descriptions are in [measure_dictionary.json](measure_dictionary.json).

## Definitions

| Metric | Calculation and denominator |
|---|---|
| Core cohort | Purchases >= 2017-01-01 and < 2018-09-01; both report pages filter Date[Core Period] = 1 |
| Eligible delivered | Status delivered, purchase/delivery/estimate timestamps present, delivery >= purchase |
| Late | Eligible and actual delivery calendar date > estimated delivery calendar date |
| On-time rate | (Eligible − Late) / Eligible; zero-denominator contexts are blank |
| Delivery days | Elapsed purchase-to-delivery seconds / 86,400, for eligible orders |
| Median / P90 | Median / inclusive continuous 90th percentile of eligible elapsed days |
| Selected review | Latest answer timestamp, then creation timestamp, then review_id descending per order |
| Average review | Mean selected score across reviewed orders in context; not limited to delivery-eligible orders |
| Post-delivery review | Selected answer timestamp >= delivery timestamp, plus delivery eligibility for the delay comparison |
| Low rating | Selected score 1 or 2; denominator is the reviewed sample, not all orders |
| Merchandise BRL | Sum item price, aggregated once per order; excludes freight; no refund adjustment |
| Late merchandise | Merchandise on late eligible orders; exposure, not loss, margin or savings |
| Approval stage | Purchase → approval, if chronology is nonnegative |
| Handoff stage | Approval → carrier handoff, if chronology is nonnegative |
| Transit stage | Carrier handoff → delivery, if chronology is nonnegative |

Stage measures use delivery-eligible orders and their own nonnegative valid samples; sample counts are displayed. Medians from different samples/stages are not additive. Source timestamps have no timezone offset; they are interpreted consistently as supplied. Calendar-date lateness avoids treating delivery during the promised day as late.

Diagnostic priority visuals use late-count ranks with at least 100 eligible orders. Dense rank can include ties; rank is a prioritization aid, not proof of poor seller performance. Anonymous seller labels use the first eight characters of source IDs. Do not infer carrier or seller fault without operational investigation.

## Quality issues preserved

- 9,803 orders have multiple item rows; 2,961 have multiple payments; 547 have multiple review rows; 1,278 have multiple sellers. Aggregate before joining.
- 775 orders have no items, one has no payment, and 768 have no review. Missing monetary values remain null; missing amounts are not converted into invented zero sales.
- Eight delivered orders lack delivery timestamps and are excluded from delivery KPIs. Out-of-sequence stage events have stage-specific exclusions.
- 303 payment-versus-item-plus-freight differences exceed BRL 0.01. They are audited, not force-balanced.
- 610 products lack category; two other categories lack English translation. Explicit labels retain coverage.
- Raw geolocation contains 261,831 duplicate full rows and nonunique ZIP prefixes. It is ingested/audited but excluded from the semantic model; joining it directly would multiply rows.
- Reviews can be answered before delivery: the selected core cohort has 4,648 such eligible-order responses. Timing affects interpretation, so the comparison visual uses post-delivery responses and analysis exports show both clocks.

The post-delivery comparison is still highly selected: it covers 1,907/6,531 late eligible orders (29.2%) versus 89,005/89,672 on-time eligible orders (99.3%). The source describes survey invitation upon receipt or when the promise is due. This timing mechanism means the observed rating difference cannot identify a delivery effect. A dynamic subtitle retains the current date/state context and reports coverage. Band-level tooltip measures explicitly remove the Review Score filter, so hovering five stars does not misleadingly report a zero low-rating rate.

## March cohort robustness

The independent raw-CSV audit in `src/audit_findings.py` checks 5,675/7,003 = 81.0367% on time in March 2018, against 83,997/89,200 = 94.1670% in all other core months. The core baseline is 89,672/96,203 = 93.2112%; it overlaps March, so the disjoint comparator is better for assessing the difference.

The unadjusted gap is -13.13 percentage points. Pooling eligible orders to define common destination-state weights produces about 80.8% versus 94.2%; this is direct standardization, not a causal model. Eligibility shares are 97.12% in March and 97.08% in the rest, so this particular gap is not explained by a large difference in observed eligibility coverage. The observed on-time share of all placed orders is 78.7% versus 91.4%; this broader descriptive measure deliberately treats noneligible orders as not demonstrated on time and must not replace the delivery-only KPI.

March's median promised calendar lead time is 22 days versus 24 in other core months. Promise-setting and destination/product/seller mix warrant investigation alongside elapsed delivery performance. No cause is identified.

The descriptive 95% Wilson-Newcombe difference interval is approximately -14.1 to -12.2 pp. It addresses binomial sampling variation under an independence approximation; repeated customers/sellers, dataset selection, observation-window censoring and post-hoc month selection remain. The interval is not a causal estimate or a preregistered test. Method reference: [Newcombe, 1998](https://pubmed.ncbi.nlm.nih.gov/9595617/).

`reports/validation/source_exceptions.csv`, `payment_reconciliation.csv` and `quality_summary.csv` retain the evidence. Hard integrity checks can pass while source exceptions remain. End-of-period cohorts and response selection can bias comparisons; the default period removes sparse outer purchase months but does not establish an extract cutoff or eliminate censoring.

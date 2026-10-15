SELECT count(*) orders, sum(delivery_eligible) eligible,
    count(*) FILTER(WHERE seller_count=1 AND delivery_eligible=1) single_seller_eligible,
    count(*) FILTER(WHERE category_count=1 AND delivery_eligible=1) single_category_eligible,
    count(*) FILTER(WHERE delivery_eligible=1 AND handoff_days IS NOT NULL) handoff_valid,
    median(approval_days) median_approval_days,
    median(handoff_days) FILTER(WHERE delivery_eligible=1) median_handoff_days,
    median(transit_days) FILTER(WHERE delivery_eligible=1) median_transit_days,
    count(*) FILTER(WHERE delivery_eligible=1 AND review_score IS NOT NULL AND post_delivery_review=1) post_delivery_reviewed
FROM mart.fact_order WHERE core_period=1;

SELECT customer_state, count(*) orders, sum(delivery_eligible) eligible,
    sum(is_late) late, sum(is_late)*1.0/nullif(sum(delivery_eligible),0) late_rate,
    median(delivery_days) median_delivery_days,
    avg(review_score) average_review,
    sum(merchandise_brl) FILTER(WHERE is_late=1) late_merchandise_exposure_brl
FROM mart.fact_order WHERE core_period=1 GROUP BY 1
HAVING sum(delivery_eligible)>=100 ORDER BY late DESC;

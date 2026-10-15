SELECT c.category, f.category_key, count(*) orders, sum(delivery_eligible) eligible,
    sum(is_late) late, sum(is_late)*1.0/nullif(sum(delivery_eligible),0) late_rate,
    count(*) FILTER(WHERE review_score IS NOT NULL) reviewed,
    avg(review_score) average_score,
    median(handoff_days) median_handoff_days, median(transit_days) median_transit_days,
    sum(merchandise_brl) FILTER(WHERE is_late=1) late_merchandise_exposure_brl
FROM mart.fact_order f JOIN mart.dim_category c USING(category_key)
WHERE core_period=1 AND category_count=1 AND delivery_eligible=1
GROUP BY 1,2 HAVING count(*)>=100 ORDER BY late DESC;

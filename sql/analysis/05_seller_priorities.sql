SELECT s.seller, s.seller_state, f.seller_key,
    count(*) eligible, sum(is_late) late, avg(is_late) late_rate,
    median(handoff_days) median_handoff_days, median(transit_days) median_transit_days,
    sum(merchandise_brl) FILTER(WHERE is_late=1) late_merchandise_exposure_brl
FROM mart.fact_order f JOIN mart.dim_seller s USING(seller_key)
WHERE core_period=1 AND seller_count=1 AND delivery_eligible=1
GROUP BY 1,2,3 HAVING count(*)>=100 ORDER BY late DESC;

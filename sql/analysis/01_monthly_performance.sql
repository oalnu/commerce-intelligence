SELECT d.month_label, count(*) orders, sum(delivery_eligible) eligible,
    sum(is_late) late, 1.0-sum(is_late)*1.0/nullif(sum(delivery_eligible),0) on_time_rate,
    median(delivery_days) median_delivery_days,
    quantile_cont(delivery_days,0.9) p90_delivery_days,
    avg(review_score) average_review
FROM mart.fact_order f JOIN mart.dim_date d USING(date_key)
WHERE f.core_period=1 GROUP BY 1 ORDER BY 1;

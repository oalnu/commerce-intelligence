-- A descriptive sensitivity check, not a causal adjustment or intervention estimate.
WITH groups AS (
    SELECT customer_state, date_trunc('month',purchased_at) purchase_month,
        count(*) FILTER(WHERE is_late=1) late_n,
        count(*) FILTER(WHERE is_late=0) on_time_n,
        count(*) FILTER(WHERE is_late=1 AND review_score<=2) late_low,
        count(*) FILTER(WHERE is_late=0 AND review_score<=2) on_time_low
    FROM mart.fact_order
    WHERE core_period=1 AND delivery_eligible=1 AND review_score IS NOT NULL AND post_delivery_review=1
    GROUP BY 1,2
), eligible AS (
    SELECT *, late_low*1.0/late_n-on_time_low*1.0/on_time_n rate_difference
    FROM groups WHERE late_n>=20 AND on_time_n>=20
)
SELECT count(*) eligible_state_months,
    count(*) FILTER(WHERE rate_difference>0) late_has_higher_low_rating,
    sum(late_n) late_reviewed, sum(on_time_n) on_time_reviewed,
    median(rate_difference) median_rate_difference
FROM eligible;

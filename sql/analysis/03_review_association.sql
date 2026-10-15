SELECT CASE WHEN post_delivery_review=1 THEN 'Answered after delivery'
            ELSE 'Answered before delivery' END review_timing,
    is_late, count(*) reviewed_orders, avg(review_score) average_score,
    count(*) FILTER(WHERE review_score<=2) low_reviews,
    count(*) FILTER(WHERE review_score<=2)*1.0/count(*) low_rating_rate
FROM mart.fact_order
WHERE core_period=1 AND delivery_eligible=1 AND review_score IS NOT NULL
GROUP BY 1,2 ORDER BY 1,2;

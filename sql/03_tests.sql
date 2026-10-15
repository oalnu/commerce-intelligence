-- Every result is a hard-failure count: zero is required.
SELECT 'order_grain' AS check_name, abs(count(*)-99441) failures FROM mart.fact_order
UNION ALL SELECT 'item_grain', abs(count(*)-112650) FROM mart.fact_item
UNION ALL SELECT 'duplicate_order_ids',count(*)-count(DISTINCT order_id) FROM mart.fact_order
UNION ALL SELECT 'order_customer_orphans',count(*) FROM core.orders o ANTI JOIN core.customer c USING(customer_id)
UNION ALL SELECT 'item_order_orphans',count(*) FROM core.item i ANTI JOIN core.orders o USING(order_id)
UNION ALL SELECT 'item_product_orphans',count(*) FROM core.item i ANTI JOIN core.product p USING(product_id)
UNION ALL SELECT 'item_seller_orphans',count(*) FROM core.item i ANTI JOIN core.seller s USING(seller_id)
UNION ALL SELECT 'payment_order_orphans',count(*) FROM core.payment p ANTI JOIN core.orders o USING(order_id)
UNION ALL SELECT 'review_order_orphans',count(*) FROM core.review r ANTI JOIN core.orders o USING(order_id)
UNION ALL SELECT 'mart_date_orphans',count(*) FROM mart.fact_order o ANTI JOIN mart.dim_date d USING(date_key)
UNION ALL SELECT 'mart_state_orphans',count(*) FROM mart.fact_order o ANTI JOIN mart.dim_customer_state d ON o.customer_state=d.state_key
UNION ALL SELECT 'mart_seller_orphans',count(*) FROM mart.fact_order o ANTI JOIN mart.dim_seller d USING(seller_key)
UNION ALL SELECT 'mart_category_orphans',count(*) FROM mart.fact_order o ANTI JOIN mart.dim_category d USING(category_key)
UNION ALL SELECT 'invalid_review_scores',count(*) FROM core.review WHERE score NOT BETWEEN 1 AND 5 OR score IS NULL
UNION ALL SELECT 'negative_money',count(*) FROM core.item WHERE price_brl<0 OR freight_brl<0
UNION ALL SELECT 'money_inflation_merchandise',
    CASE WHEN (SELECT sum(merchandise_brl) FROM mart.fact_order)=(SELECT sum(price_brl) FROM core.item) THEN 0 ELSE 1 END
UNION ALL SELECT 'money_inflation_freight',
    CASE WHEN (SELECT sum(freight_brl) FROM mart.fact_order)=(SELECT sum(freight_brl) FROM core.item) THEN 0 ELSE 1 END
UNION ALL SELECT 'money_inflation_payment',
    CASE WHEN (SELECT sum(payment_brl) FROM mart.fact_order)=(SELECT sum(payment_brl) FROM core.payment) THEN 0 ELSE 1 END
UNION ALL SELECT 'delivery_partition',count(*) FROM mart.fact_order
    WHERE delivery_eligible IS NULL OR delivery_eligible NOT IN (0,1)
       OR (delivery_eligible=1 AND (is_late IS NULL OR is_late NOT IN (0,1)))
       OR (delivery_eligible=0 AND is_late IS NOT NULL)
UNION ALL SELECT 'negative_valid_delivery_duration',count(*) FROM mart.fact_order WHERE delivery_days<0
UNION ALL SELECT 'selected_review_grain',count(*)-count(DISTINCT order_id) FROM core.selected_review
UNION ALL SELECT 'pinned_calendar_late_baseline',abs(count(*)-6534) FROM mart.fact_order WHERE is_late=1
UNION ALL SELECT 'pinned_delivery_eligible_baseline',abs(count(*)-96470) FROM mart.fact_order WHERE delivery_eligible=1
UNION ALL SELECT 'eligible_required_dates',count(*) FROM mart.fact_order
    WHERE delivery_eligible=1 AND (purchased_at IS NULL OR delivered_at IS NULL OR estimated_at IS NULL OR delivered_at<purchased_at OR order_status<>'delivered')
UNION ALL SELECT 'late_date_consistency',count(*) FROM mart.fact_order
    WHERE delivery_eligible=1 AND is_late IS DISTINCT FROM CAST(CAST(delivered_at AS DATE)>CAST(estimated_at AS DATE) AS INTEGER)
UNION ALL SELECT 'duration_null_contract',count(*) FROM mart.fact_order
    WHERE (delivery_eligible=1 AND delivery_days IS NULL) OR (delivery_eligible=0 AND delivery_days IS NOT NULL)
UNION ALL SELECT 'negative_or_missing_payment',count(*) FROM core.payment WHERE payment_brl<0 OR payment_brl IS NULL
UNION ALL SELECT 'missing_item_money',count(*) FROM core.item WHERE price_brl IS NULL OR freight_brl IS NULL
UNION ALL SELECT 'item_fact_product_orphans',count(*) FROM mart.fact_item i ANTI JOIN mart.dim_product p USING(product_id)
UNION ALL SELECT 'item_fact_order_orphans',count(*) FROM mart.fact_item i ANTI JOIN mart.fact_order o USING(order_id)
UNION ALL SELECT 'seller_alias_collisions',count(*)-count(DISTINCT seller) FROM mart.dim_seller
UNION ALL SELECT 'review_timing_contract',count(*) FROM mart.fact_order
    WHERE post_delivery_review IS DISTINCT FROM CASE WHEN review_answered_at>=delivered_at AND delivered_at IS NOT NULL THEN 1 ELSE 0 END;

-- Aggregate independent children BEFORE joining them to the order header.
CREATE OR REPLACE TABLE mart.fact_order AS
WITH items AS (
    SELECT i.order_id, count(*) item_count,
        count(DISTINCT i.seller_id) seller_count,
        count(DISTINCT p.category_key) category_count,
        CASE WHEN count(DISTINCT i.seller_id)=1 THEN min(i.seller_id) ELSE '__multiple__' END seller_key,
        CASE WHEN count(DISTINCT p.category_key)=1 THEN min(p.category_key) ELSE '__multiple__' END category_key,
        sum(i.price_brl)::DECIMAL(18,2) merchandise_brl,
        sum(i.freight_brl)::DECIMAL(18,2) freight_brl
    FROM core.item i JOIN core.product p USING(product_id) GROUP BY i.order_id
), payments AS (
    SELECT order_id, count(*) payment_count, sum(payment_brl)::DECIMAL(18,2) payment_brl
    FROM core.payment GROUP BY order_id
), reviews AS (
    SELECT order_id, count(*) review_count FROM core.review GROUP BY order_id
), base AS (
    SELECT o.*, c.customer_unique_id, c.state customer_state,
        CAST(strftime(o.purchased_at,'%Y%m%d') AS INTEGER) date_key,
        CAST(o.purchased_at AS DATE) purchase_date,
        CASE WHEN o.purchased_at >= TIMESTAMP '2017-01-01'
                   AND o.purchased_at < TIMESTAMP '2018-09-01' THEN 1 ELSE 0 END core_period,
        COALESCE(i.item_count,0)::INTEGER item_count,
        COALESCE(i.seller_count,0)::INTEGER seller_count,
        COALESCE(i.category_count,0)::INTEGER category_count,
        COALESCE(i.seller_key,'__no_items__') seller_key,
        COALESCE(i.category_key,'__no_items__') category_key,
        i.merchandise_brl, i.freight_brl, p.payment_brl,
        COALESCE(p.payment_count,0)::INTEGER payment_count,
        COALESCE(rc.review_count,0)::INTEGER review_count,
        r.score review_score, r.answered_at review_answered_at,
        CASE WHEN o.order_status='delivered' AND o.delivered_at IS NOT NULL
                   AND o.estimated_at IS NOT NULL AND o.delivered_at >= o.purchased_at
             THEN 1 ELSE 0 END delivery_eligible,
        CASE WHEN r.answered_at >= o.delivered_at AND o.delivered_at IS NOT NULL
             THEN 1 ELSE 0 END post_delivery_review
    FROM core.orders o
    JOIN core.customer c USING(customer_id)
    LEFT JOIN items i USING(order_id)
    LEFT JOIN payments p USING(order_id)
    LEFT JOIN reviews rc USING(order_id)
    LEFT JOIN core.selected_review r USING(order_id)
)
SELECT *,
    CASE WHEN delivery_eligible=1 THEN
        CASE WHEN CAST(delivered_at AS DATE)>CAST(estimated_at AS DATE) THEN 1 ELSE 0 END
    END is_late,
    CASE WHEN delivery_eligible=1 THEN date_diff('second',purchased_at,delivered_at)/86400.0 END delivery_days,
    CASE WHEN delivery_eligible=1 THEN greatest(0,date_diff('day',CAST(estimated_at AS DATE),CAST(delivered_at AS DATE))) END late_days,
    CASE WHEN approved_at >= purchased_at THEN date_diff('second',purchased_at,approved_at)/86400.0 END approval_days,
    CASE WHEN carrier_at >= approved_at THEN date_diff('second',approved_at,carrier_at)/86400.0 END handoff_days,
    CASE WHEN delivered_at >= carrier_at THEN date_diff('second',carrier_at,delivered_at)/86400.0 END transit_days,
    CASE WHEN delivery_eligible=0 THEN 'Not eligible'
         WHEN CAST(delivered_at AS DATE)<=CAST(estimated_at AS DATE) THEN 'On time'
         WHEN date_diff('day',CAST(estimated_at AS DATE),CAST(delivered_at AS DATE))<=3 THEN '1–3 days late'
         WHEN date_diff('day',CAST(estimated_at AS DATE),CAST(delivered_at AS DATE))<=7 THEN '4–7 days late'
         ELSE '8+ days late' END delay_band,
    CASE WHEN delivery_eligible=0 THEN 0
         WHEN CAST(delivered_at AS DATE)<=CAST(estimated_at AS DATE) THEN 1
         WHEN date_diff('day',CAST(estimated_at AS DATE),CAST(delivered_at AS DATE))<=3 THEN 2
         WHEN date_diff('day',CAST(estimated_at AS DATE),CAST(delivered_at AS DATE))<=7 THEN 3
         ELSE 4 END delay_band_sort
FROM base;
ALTER TABLE mart.fact_order ADD PRIMARY KEY(order_id);

CREATE OR REPLACE TABLE mart.fact_item AS
SELECT order_id, item_number, product_id, seller_id,
    price_brl, freight_brl FROM core.item;
ALTER TABLE mart.fact_item ADD PRIMARY KEY(order_id,item_number);

CREATE OR REPLACE TABLE mart.dim_date AS
SELECT CAST(strftime(d,'%Y%m%d') AS INTEGER) date_key,
    CAST(d AS DATE) AS date, year(d)::INTEGER AS year_number, month(d)::INTEGER AS month_number,
    strftime(d,'%Y-%m') month_label, CAST(date_trunc('month',d) AS DATE) month_start,
    CASE WHEN d>=DATE '2017-01-01' AND d<DATE '2018-09-01' THEN 1 ELSE 0 END core_period
FROM generate_series(DATE '2016-01-01',DATE '2018-12-31',INTERVAL 1 DAY) t(d);
ALTER TABLE mart.dim_date ADD PRIMARY KEY(date_key);

CREATE OR REPLACE TABLE mart.dim_customer_state AS
SELECT DISTINCT state state_key, state FROM core.customer;
ALTER TABLE mart.dim_customer_state ADD PRIMARY KEY(state_key);

CREATE OR REPLACE TABLE mart.dim_seller AS
SELECT seller_id seller_key, 'Seller ' || upper(left(seller_id,8)) seller,
    state seller_state, city seller_city FROM core.seller
UNION ALL SELECT '__multiple__','Multiple sellers','N/A','N/A'
UNION ALL SELECT '__no_items__','No order items','N/A','N/A';
ALTER TABLE mart.dim_seller ADD PRIMARY KEY(seller_key);

CREATE OR REPLACE TABLE mart.dim_category AS
SELECT DISTINCT category_key, category FROM core.product
UNION ALL SELECT '__multiple__','Multiple categories'
UNION ALL SELECT '__no_items__','No order items';
ALTER TABLE mart.dim_category ADD PRIMARY KEY(category_key);

CREATE OR REPLACE TABLE mart.dim_product AS SELECT * FROM core.product;
ALTER TABLE mart.dim_product ADD PRIMARY KEY(product_id);
CREATE OR REPLACE TABLE mart.dim_status AS
SELECT DISTINCT order_status FROM core.orders;
ALTER TABLE mart.dim_status ADD PRIMARY KEY(order_status);

-- Presentation metadata, not synthetic observations.
CREATE OR REPLACE TABLE mart.dim_stage AS
SELECT * FROM (VALUES (1,'Approval'),(2,'Seller handoff'),(3,'Transit')) t(stage_order,stage);
ALTER TABLE mart.dim_stage ADD PRIMARY KEY(stage_order);

CREATE OR REPLACE TABLE audit.payment_reconciliation AS
SELECT order_id, order_status, merchandise_brl, freight_brl, payment_brl,
    (payment_brl-merchandise_brl-freight_brl)::DECIMAL(18,2) difference_brl
FROM mart.fact_order
WHERE merchandise_brl IS NOT NULL AND payment_brl IS NOT NULL
  AND abs(payment_brl-merchandise_brl-freight_brl)>0.01;

CREATE OR REPLACE TABLE audit.quality_summary AS
SELECT 'Delivered without actual timestamp' issue, count(*)::INTEGER affected_rows
FROM mart.fact_order WHERE order_status='delivered' AND delivered_at IS NULL
UNION ALL SELECT 'Orders without items', count(*) FROM mart.fact_order WHERE item_count=0
UNION ALL SELECT 'Orders without payments', count(*) FROM mart.fact_order WHERE payment_count=0
UNION ALL SELECT 'Orders without reviews', count(*) FROM mart.fact_order WHERE review_count=0
UNION ALL SELECT 'Orders with multiple reviews', count(*) FROM mart.fact_order WHERE review_count>1
UNION ALL SELECT 'Payment mismatch greater than BRL 0.01', count(*) FROM audit.payment_reconciliation
UNION ALL SELECT 'Selected reviews answered before delivery', count(*) FROM mart.fact_order
  WHERE review_answered_at < delivered_at;

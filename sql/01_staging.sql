CREATE SCHEMA IF NOT EXISTS stg;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS mart;
CREATE SCHEMA IF NOT EXISTS audit;

CREATE OR REPLACE TABLE stg.orders AS
SELECT order_id, customer_id, order_status,
    CAST(order_purchase_timestamp AS TIMESTAMP) purchased_at,
    CAST(NULLIF(order_approved_at, '') AS TIMESTAMP) approved_at,
    CAST(NULLIF(order_delivered_carrier_date, '') AS TIMESTAMP) carrier_at,
    CAST(NULLIF(order_delivered_customer_date, '') AS TIMESTAMP) delivered_at,
    CAST(order_estimated_delivery_date AS TIMESTAMP) estimated_at
FROM raw.orders;

CREATE OR REPLACE TABLE core.customer AS
SELECT customer_id, customer_unique_id,
    lpad(customer_zip_code_prefix,5,'0') zip_prefix,
    customer_city city, customer_state state
FROM raw.customers;
ALTER TABLE core.customer ADD PRIMARY KEY (customer_id);

CREATE OR REPLACE TABLE core.seller AS
SELECT seller_id, lpad(seller_zip_code_prefix,5,'0') zip_prefix,
    seller_city city, seller_state state FROM raw.sellers;
ALTER TABLE core.seller ADD PRIMARY KEY (seller_id);

CREATE OR REPLACE TABLE core.product AS
SELECT p.product_id,
    COALESCE(NULLIF(p.product_category_name,''), '__unknown__') category_key,
    CASE WHEN NULLIF(p.product_category_name,'') IS NULL THEN 'Unknown category'
         WHEN t.product_category_name_english IS NOT NULL THEN replace(t.product_category_name_english,'_',' ')
         WHEN p.product_category_name = 'pc_gamer' THEN 'PC gaming (manual translation)'
         WHEN p.product_category_name = 'portateis_cozinha_e_preparadores_de_alimentos'
              THEN 'Portable kitchen and food preparation (manual translation)'
         ELSE replace(p.product_category_name,'_',' ') END category,
    CAST(NULLIF(p.product_weight_g,'') AS INTEGER) weight_g,
    CAST(NULLIF(p.product_length_cm,'') AS INTEGER) length_cm,
    CAST(NULLIF(p.product_height_cm,'') AS INTEGER) height_cm,
    CAST(NULLIF(p.product_width_cm,'') AS INTEGER) width_cm
FROM raw.products p
LEFT JOIN raw.category_translation t USING(product_category_name);
ALTER TABLE core.product ADD PRIMARY KEY(product_id);

CREATE OR REPLACE TABLE core.orders AS
SELECT * FROM stg.orders;
ALTER TABLE core.orders ADD PRIMARY KEY(order_id);

CREATE OR REPLACE TABLE core.item AS
SELECT order_id, CAST(order_item_id AS INTEGER) item_number, product_id, seller_id,
    CAST(shipping_limit_date AS TIMESTAMP) shipping_limit_at,
    CAST(price AS DECIMAL(18,2)) price_brl,
    CAST(freight_value AS DECIMAL(18,2)) freight_brl
FROM raw.order_items;
ALTER TABLE core.item ADD PRIMARY KEY(order_id,item_number);

CREATE OR REPLACE TABLE core.payment AS
SELECT order_id, CAST(payment_sequential AS INTEGER) payment_sequence,
    payment_type, CAST(payment_installments AS INTEGER) installments,
    CAST(payment_value AS DECIMAL(18,2)) payment_brl
FROM raw.order_payments;
ALTER TABLE core.payment ADD PRIMARY KEY(order_id,payment_sequence);

CREATE OR REPLACE TABLE core.review AS
SELECT review_id, order_id, CAST(review_score AS INTEGER) score,
    CAST(review_creation_date AS TIMESTAMP) created_at,
    CAST(review_answer_timestamp AS TIMESTAMP) answered_at
FROM raw.order_reviews;
ALTER TABLE core.review ADD PRIMARY KEY(review_id,order_id);

-- Preserve every review event; only this view chooses one response per order.
CREATE OR REPLACE VIEW core.selected_review AS
SELECT *, row_number() OVER (
    PARTITION BY order_id ORDER BY answered_at DESC, created_at DESC, review_id DESC
) selection_rank
FROM core.review
QUALIFY selection_rank = 1;

CREATE OR REPLACE TABLE audit.source_exceptions AS
SELECT 'missing_delivery_timestamp' issue, order_id entity_id,
       'Delivered status without actual delivery timestamp' detail
FROM core.orders WHERE order_status='delivered' AND delivered_at IS NULL
UNION ALL
SELECT 'carrier_before_approval', order_id, 'Stage chronology anomaly'
FROM core.orders WHERE carrier_at < approved_at
UNION ALL
SELECT 'delivery_before_carrier', order_id, 'Stage chronology anomaly'
FROM core.orders WHERE delivered_at < carrier_at
UNION ALL
SELECT 'missing_product_category', product_id, 'Unknown category retained'
FROM raw.products WHERE NULLIF(product_category_name,'') IS NULL
UNION ALL
SELECT 'untranslated_source_category', p.product_id, p.product_category_name
FROM raw.products p LEFT JOIN raw.category_translation t USING(product_category_name)
WHERE NULLIF(p.product_category_name,'') IS NOT NULL AND t.product_category_name IS NULL;

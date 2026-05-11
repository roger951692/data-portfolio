-- ============================================================
-- E-Commerce Analytics Warehouse — Schema
-- Source : Olist Brazilian E-Commerce Public Dataset
-- Style  : Star schema with five dimensions and three facts.
-- Tested : SQLite 3 + PostgreSQL 14 (one schema, two engines)
-- ============================================================
--
-- Olist ships 9 raw CSV tables. The DDL below mirrors them 1-to-1
-- (so loading the raw data is `\copy` / `pd.read_csv` and the
-- column names match), and then defines a small star schema in
-- the `analytics` schema for downstream querying.
--
-- ============================================================

-- ----------------------------------------------------------------
-- 1. RAW LAYER — exact mirror of Olist CSV columns
-- ----------------------------------------------------------------

DROP TABLE IF EXISTS raw_customers;
DROP TABLE IF EXISTS raw_geolocation;
DROP TABLE IF EXISTS raw_order_items;
DROP TABLE IF EXISTS raw_order_payments;
DROP TABLE IF EXISTS raw_order_reviews;
DROP TABLE IF EXISTS raw_orders;
DROP TABLE IF EXISTS raw_products;
DROP TABLE IF EXISTS raw_sellers;
DROP TABLE IF EXISTS raw_category_translation;

CREATE TABLE raw_customers (
    customer_id              TEXT PRIMARY KEY,
    customer_unique_id       TEXT,
    customer_zip_code_prefix TEXT,
    customer_city            TEXT,
    customer_state           TEXT
);

CREATE TABLE raw_geolocation (
    geolocation_zip_code_prefix TEXT,
    geolocation_lat             REAL,
    geolocation_lng             REAL,
    geolocation_city            TEXT,
    geolocation_state           TEXT
);

CREATE TABLE raw_orders (
    order_id                       TEXT PRIMARY KEY,
    customer_id                    TEXT,
    order_status                   TEXT,
    order_purchase_timestamp       TEXT,
    order_approved_at              TEXT,
    order_delivered_carrier_date   TEXT,
    order_delivered_customer_date  TEXT,
    order_estimated_delivery_date  TEXT
);

CREATE TABLE raw_order_items (
    order_id            TEXT,
    order_item_id       INTEGER,
    product_id          TEXT,
    seller_id           TEXT,
    shipping_limit_date TEXT,
    price               REAL,
    freight_value       REAL,
    PRIMARY KEY (order_id, order_item_id)
);

CREATE TABLE raw_order_payments (
    order_id              TEXT,
    payment_sequential    INTEGER,
    payment_type          TEXT,
    payment_installments  INTEGER,
    payment_value         REAL,
    PRIMARY KEY (order_id, payment_sequential)
);

CREATE TABLE raw_order_reviews (
    review_id                TEXT,
    order_id                 TEXT,
    review_score             INTEGER,
    review_comment_title     TEXT,
    review_comment_message   TEXT,
    review_creation_date     TEXT,
    review_answer_timestamp  TEXT
);

CREATE TABLE raw_products (
    product_id                  TEXT PRIMARY KEY,
    product_category_name       TEXT,
    product_name_lenght         INTEGER,
    product_description_lenght  INTEGER,
    product_photos_qty          INTEGER,
    product_weight_g            INTEGER,
    product_length_cm           INTEGER,
    product_height_cm           INTEGER,
    product_width_cm            INTEGER
);

CREATE TABLE raw_sellers (
    seller_id              TEXT PRIMARY KEY,
    seller_zip_code_prefix TEXT,
    seller_city            TEXT,
    seller_state           TEXT
);

CREATE TABLE raw_category_translation (
    product_category_name         TEXT PRIMARY KEY,
    product_category_name_english TEXT
);

-- ----------------------------------------------------------------
-- 2. ANALYTICS LAYER — star schema fed by the ETL notebook
--    notebooks/01_etl_and_features.ipynb populates these.
-- ----------------------------------------------------------------

DROP TABLE IF EXISTS fact_payments;
DROP TABLE IF EXISTS fact_order_items;
DROP TABLE IF EXISTS fact_orders;
DROP TABLE IF EXISTS dim_seller;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_date;

CREATE TABLE dim_date (
    date         DATE PRIMARY KEY,
    year         INTEGER,
    quarter      INTEGER,
    month        INTEGER,
    month_label  TEXT,
    weekday      INTEGER,
    weekday_name TEXT,
    is_weekend   INTEGER
);

CREATE TABLE dim_customer (
    customer_id    TEXT PRIMARY KEY,
    customer_state TEXT,
    customer_city  TEXT,
    cohort_month   TEXT
);

CREATE TABLE dim_product (
    product_id   TEXT PRIMARY KEY,
    category     TEXT,
    category_en  TEXT,
    weight_g     INTEGER,
    volume_cm3   INTEGER,
    photos_qty   INTEGER
);

CREATE TABLE dim_seller (
    seller_id    TEXT PRIMARY KEY,
    seller_state TEXT,
    seller_city  TEXT
);

CREATE TABLE fact_orders (
    order_id              TEXT PRIMARY KEY,
    customer_id           TEXT REFERENCES dim_customer(customer_id),
    order_status          TEXT,
    order_purchase_ts     TEXT,
    delivered_ts          TEXT,
    estimated_ts          TEXT,
    delivery_delay_days   INTEGER,   -- positive = late
    is_late               INTEGER,   -- 1 / 0
    review_score          INTEGER,
    total_items           INTEGER,
    revenue               REAL,
    freight               REAL,
    payment_methods       INTEGER,   -- distinct payment types on the order
    payment_installments  INTEGER    -- max installments on the order
);

CREATE TABLE fact_order_items (
    order_id      TEXT REFERENCES fact_orders(order_id),
    order_item_id INTEGER,
    product_id    TEXT REFERENCES dim_product(product_id),
    seller_id     TEXT REFERENCES dim_seller(seller_id),
    price         REAL,
    freight_value REAL,
    PRIMARY KEY (order_id, order_item_id)
);

CREATE TABLE fact_payments (
    order_id             TEXT REFERENCES fact_orders(order_id),
    payment_sequential   INTEGER,
    payment_type         TEXT,
    payment_installments INTEGER,
    payment_value        REAL,
    PRIMARY KEY (order_id, payment_sequential)
);

-- ----------------------------------------------------------------
-- 3. INDEXES (helpful once the tables are populated)
-- ----------------------------------------------------------------

CREATE INDEX idx_fact_orders_customer ON fact_orders(customer_id);
CREATE INDEX idx_fact_orders_status   ON fact_orders(order_status);
CREATE INDEX idx_fact_items_product   ON fact_order_items(product_id);
CREATE INDEX idx_fact_items_seller    ON fact_order_items(seller_id);
CREATE INDEX idx_fact_payments_type   ON fact_payments(payment_type);

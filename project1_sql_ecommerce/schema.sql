-- ============================================================
-- E-Commerce Portfolio Database — Schema
-- Stack : PostgreSQL 14+ (compatible with most modern dialects)
-- ============================================================
--
-- Five tables modelling a small e-commerce shop:
--   customers   — buyer master data
--   products    — catalogue with cost prices for margin analysis
--   orders      — order header (with status: completed / cancelled / refunded)
--   order_items — order lines (FK to orders + products)
--   payments    — payment events (one row per settled order)
--
-- Run order:
--   1) schema.sql      (this file — DDL only)
--   2) seed_data.sql   (sample data)
--   3) queries.sql     (analytical queries)
--
-- For an SQLite alternative, see schema_sqlite.sql.
-- ============================================================

DROP TABLE IF EXISTS payments    CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders      CASCADE;
DROP TABLE IF EXISTS products    CASCADE;
DROP TABLE IF EXISTS customers   CASCADE;

-- ============================================================
-- TABLES
-- ============================================================

CREATE TABLE customers (
    customer_id  SERIAL       PRIMARY KEY,
    name         VARCHAR(100) NOT NULL,
    city         VARCHAR(50),
    signup_date  DATE         NOT NULL
);

CREATE TABLE products (
    product_id   SERIAL        PRIMARY KEY,
    name         VARCHAR(100)  NOT NULL,
    category     VARCHAR(50),
    cost_price   NUMERIC(10,2) NOT NULL CHECK (cost_price >= 0)
);

CREATE TABLE orders (
    order_id     SERIAL      PRIMARY KEY,
    customer_id  INT         NOT NULL REFERENCES customers(customer_id),
    order_date   DATE        NOT NULL,
    status       VARCHAR(20) NOT NULL DEFAULT 'completed'
                 CHECK (status IN ('completed', 'cancelled', 'refunded', 'pending'))
);

CREATE TABLE order_items (
    item_id      SERIAL        PRIMARY KEY,
    order_id     INT           NOT NULL REFERENCES orders(order_id),
    product_id   INT           NOT NULL REFERENCES products(product_id),
    quantity     INT           NOT NULL CHECK (quantity > 0),
    unit_price   NUMERIC(10,2) NOT NULL CHECK (unit_price >= 0)
);

CREATE TABLE payments (
    payment_id    SERIAL        PRIMARY KEY,
    order_id      INT           NOT NULL REFERENCES orders(order_id),
    amount        NUMERIC(10,2) NOT NULL CHECK (amount >= 0),
    payment_date  DATE          NOT NULL,
    method        VARCHAR(20)   CHECK (method IN ('card', 'paypal', 'transfer'))
);

-- ============================================================
-- INDEXES
-- (used by the optimisation demo in Query 10)
-- ============================================================

CREATE INDEX idx_orders_customer     ON orders(customer_id);
CREATE INDEX idx_orders_date         ON orders(order_date);
CREATE INDEX idx_order_items_order   ON order_items(order_id);
CREATE INDEX idx_order_items_product ON order_items(product_id);
CREATE INDEX idx_payments_order      ON payments(order_id);
CREATE INDEX idx_payments_date       ON payments(payment_date);

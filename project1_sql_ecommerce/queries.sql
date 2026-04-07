-- ============================================================
-- E-Commerce SQL Analysis — Portfolio Queries
-- Author: Roger | Stack: PostgreSQL
-- ============================================================


-- ============================================================
-- QUERY 01: Monthly Revenue Trend
-- Goal: Track total revenue per month (completed orders only)
-- Concepts: DATE_TRUNC, GROUP BY, aggregation, ORDER BY
-- ============================================================

SELECT
    DATE_TRUNC('month', p.payment_date)  AS month,
    COUNT(DISTINCT o.order_id)            AS total_orders,
    SUM(oi.quantity * oi.unit_price)      AS gross_revenue,
    ROUND(AVG(oi.quantity * oi.unit_price), 2) AS avg_order_value
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
JOIN payments p     ON o.order_id = p.order_id
WHERE o.status = 'completed'
GROUP BY DATE_TRUNC('month', p.payment_date)
ORDER BY month;


-- ============================================================
-- QUERY 02: Top 10 Products by Gross Margin
-- Goal: Rank products by (revenue - cost), identify most profitable
-- Concepts: JOIN, calculated fields, ORDER BY, LIMIT
-- ============================================================

SELECT
    p.product_id,
    p.name                                               AS product_name,
    p.category,
    SUM(oi.quantity)                                     AS units_sold,
    ROUND(SUM(oi.quantity * oi.unit_price), 2)           AS total_revenue,
    ROUND(SUM(oi.quantity * p.cost_price), 2)            AS total_cost,
    ROUND(SUM(oi.quantity * (oi.unit_price - p.cost_price)), 2) AS gross_margin,
    ROUND(
        100.0 * SUM(oi.quantity * (oi.unit_price - p.cost_price))
        / NULLIF(SUM(oi.quantity * oi.unit_price), 0),
    1)                                                   AS margin_pct
FROM products p
JOIN order_items oi ON p.product_id = oi.product_id
JOIN orders o       ON oi.order_id  = o.order_id
WHERE o.status = 'completed'
GROUP BY p.product_id, p.name, p.category
ORDER BY gross_margin DESC
LIMIT 10;


-- ============================================================
-- QUERY 03: Customer Lifetime Value (LTV)
-- Goal: Total spend per customer, ranked
-- Concepts: CTE, JOIN, aggregation, RANK window function
-- ============================================================

WITH customer_spend AS (
    SELECT
        c.customer_id,
        c.name,
        c.city,
        c.signup_date,
        COUNT(DISTINCT o.order_id)              AS total_orders,
        SUM(oi.quantity * oi.unit_price)         AS lifetime_value,
        MIN(o.order_date)                        AS first_order,
        MAX(o.order_date)                        AS last_order
    FROM customers c
    JOIN orders o      ON c.customer_id = o.customer_id
    JOIN order_items oi ON o.order_id   = oi.order_id
    WHERE o.status = 'completed'
    GROUP BY c.customer_id, c.name, c.city, c.signup_date
)
SELECT
    *,
    RANK() OVER (ORDER BY lifetime_value DESC) AS ltv_rank,
    ROUND(lifetime_value / total_orders, 2)    AS avg_order_value
FROM customer_spend
ORDER BY ltv_rank;


-- ============================================================
-- QUERY 04: Cohort Retention Analysis
-- Goal: For each signup cohort (month), how many customers
--       placed orders in subsequent months?
-- Concepts: CTE, DATE_TRUNC, window functions, self-join pattern
-- ============================================================

WITH cohorts AS (
    SELECT
        c.customer_id,
        DATE_TRUNC('month', c.signup_date)  AS cohort_month,
        DATE_TRUNC('month', o.order_date)   AS order_month
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.status = 'completed'
),
cohort_sizes AS (
    SELECT
        cohort_month,
        COUNT(DISTINCT customer_id) AS cohort_size
    FROM cohorts
    GROUP BY cohort_month
),
retention AS (
    SELECT
        c.cohort_month,
        c.order_month,
        COUNT(DISTINCT c.customer_id) AS active_customers,
        EXTRACT(MONTH FROM AGE(c.order_month, c.cohort_month))::INT AS months_since_signup
    FROM cohorts c
    GROUP BY c.cohort_month, c.order_month
)
SELECT
    r.cohort_month,
    r.months_since_signup,
    r.active_customers,
    cs.cohort_size,
    ROUND(100.0 * r.active_customers / cs.cohort_size, 1) AS retention_pct
FROM retention r
JOIN cohort_sizes cs ON r.cohort_month = cs.cohort_month
ORDER BY r.cohort_month, r.months_since_signup;


-- ============================================================
-- QUERY 05: RFM Customer Segmentation
-- Goal: Segment customers into 27 RFM groups (3x3x3)
-- Concepts: CTEs, NTILE, CASE, composite scoring
-- ============================================================

WITH rfm_raw AS (
    SELECT
        c.customer_id,
        c.name,
        MAX(o.order_date)                        AS last_order_date,
        COUNT(DISTINCT o.order_id)               AS frequency,
        SUM(oi.quantity * oi.unit_price)         AS monetary
    FROM customers c
    JOIN orders o       ON c.customer_id = o.customer_id
    JOIN order_items oi ON o.order_id    = oi.order_id
    WHERE o.status = 'completed'
    GROUP BY c.customer_id, c.name
),
rfm_scores AS (
    SELECT
        *,
        NTILE(3) OVER (ORDER BY last_order_date DESC) AS r_score, -- 3=most recent
        NTILE(3) OVER (ORDER BY frequency DESC)        AS f_score,
        NTILE(3) OVER (ORDER BY monetary DESC)         AS m_score
    FROM rfm_raw
)
SELECT
    customer_id,
    name,
    last_order_date,
    frequency,
    ROUND(monetary, 2) AS monetary,
    r_score, f_score, m_score,
    (r_score + f_score + m_score) AS rfm_total,
    CASE
        WHEN (r_score + f_score + m_score) >= 8 THEN 'Champions'
        WHEN (r_score + f_score + m_score) >= 6 THEN 'Loyal Customers'
        WHEN r_score = 3 AND (f_score + m_score) <= 3 THEN 'New Customers'
        WHEN r_score <= 2 AND f_score >= 2           THEN 'At Risk'
        ELSE 'Need Attention'
    END AS segment
FROM rfm_scores
ORDER BY rfm_total DESC;


-- ============================================================
-- QUERY 06: First Purchase vs Repeat Purchase Rate
-- Goal: Identify which orders are first-time vs repeat
-- Concepts: ROW_NUMBER, LAG window functions
-- ============================================================

WITH ranked_orders AS (
    SELECT
        o.order_id,
        o.customer_id,
        c.name,
        o.order_date,
        ROW_NUMBER() OVER (
            PARTITION BY o.customer_id
            ORDER BY o.order_date
        ) AS order_rank,
        LAG(o.order_date) OVER (
            PARTITION BY o.customer_id
            ORDER BY o.order_date
        ) AS previous_order_date
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE o.status = 'completed'
)
SELECT
    order_id,
    customer_id,
    name,
    order_date,
    order_rank,
    CASE WHEN order_rank = 1 THEN 'First Purchase' ELSE 'Repeat Purchase' END AS purchase_type,
    previous_order_date,
    (order_date - previous_order_date) AS days_since_last_order
FROM ranked_orders
ORDER BY customer_id, order_rank;


-- ============================================================
-- QUERY 07: Year-over-Year Revenue by Category
-- Goal: Compare category revenue between 2022 and 2023
-- Concepts: DATE_PART, conditional aggregation (FILTER), ratio
-- ============================================================

SELECT
    p.category,
    ROUND(SUM(oi.quantity * oi.unit_price)
        FILTER (WHERE DATE_PART('year', o.order_date) = 2022), 2) AS revenue_2022,
    ROUND(SUM(oi.quantity * oi.unit_price)
        FILTER (WHERE DATE_PART('year', o.order_date) = 2023), 2) AS revenue_2023,
    ROUND(
        100.0 * (
            SUM(oi.quantity * oi.unit_price) FILTER (WHERE DATE_PART('year', o.order_date) = 2023)
            - SUM(oi.quantity * oi.unit_price) FILTER (WHERE DATE_PART('year', o.order_date) = 2022)
        ) / NULLIF(
            SUM(oi.quantity * oi.unit_price) FILTER (WHERE DATE_PART('year', o.order_date) = 2022)
        , 0),
    1) AS yoy_growth_pct
FROM products p
JOIN order_items oi ON p.product_id  = oi.product_id
JOIN orders o       ON oi.order_id   = o.order_id
WHERE o.status = 'completed'
GROUP BY p.category
ORDER BY revenue_2023 DESC NULLS LAST;


-- ============================================================
-- QUERY 08: Data Quality — Orders Without Payment
-- Goal: Find completed/active orders that have no payment record
-- Concepts: LEFT JOIN, IS NULL (anti-join pattern)
-- ============================================================

SELECT
    o.order_id,
    o.customer_id,
    c.name        AS customer_name,
    o.order_date,
    o.status,
    SUM(oi.quantity * oi.unit_price) AS order_total
FROM orders o
LEFT JOIN payments p  ON o.order_id    = p.order_id
JOIN customers c      ON o.customer_id = c.customer_id
JOIN order_items oi   ON o.order_id    = oi.order_id
WHERE p.payment_id IS NULL        -- no payment found
  AND o.status NOT IN ('cancelled', 'refunded')
GROUP BY o.order_id, o.customer_id, c.name, o.order_date, o.status
ORDER BY o.order_date;


-- ============================================================
-- QUERY 09: Running Total Revenue (Cumulative)
-- Goal: Show daily revenue + running total for the full period
-- Concepts: SUM OVER (window function), ORDER BY in window
-- ============================================================

WITH daily_revenue AS (
    SELECT
        p.payment_date            AS day,
        SUM(p.amount)             AS daily_revenue
    FROM payments p
    JOIN orders o ON p.order_id = o.order_id
    WHERE o.status = 'completed'
    GROUP BY p.payment_date
)
SELECT
    day,
    ROUND(daily_revenue, 2)    AS daily_revenue,
    ROUND(SUM(daily_revenue) OVER (
        ORDER BY day
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ), 2)                      AS running_total,
    ROUND(AVG(daily_revenue) OVER (
        ORDER BY day
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 2)                      AS rolling_7day_avg
FROM daily_revenue
ORDER BY day;


-- ============================================================
-- QUERY 10: Query Performance — Index Strategy Demo
-- Goal: Show difference between a sequential scan and an
--       index-supported query. Use EXPLAIN ANALYZE to compare.
-- Concepts: Index usage, execution plans, query optimization
-- ============================================================

-- Step 1: Run this and inspect the execution plan
EXPLAIN ANALYZE
SELECT
    o.order_id,
    o.order_date,
    c.name,
    SUM(oi.quantity * oi.unit_price) AS order_total
FROM orders o
JOIN customers c   ON o.customer_id = c.customer_id
JOIN order_items oi ON o.order_id   = oi.order_id
WHERE o.order_date BETWEEN '2023-01-01' AND '2023-06-30'
  AND o.status = 'completed'
GROUP BY o.order_id, o.order_date, c.name
ORDER BY order_total DESC;

-- Step 2: The index on orders(order_date) created in schema.sql
-- allows PostgreSQL to use an Index Scan instead of Seq Scan.
-- Without the index, the planner would scan the full orders table.
-- With idx_orders_date, it reads only rows in the date range.

-- Step 3: Check which indexes exist on a table
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('orders', 'order_items', 'payments')
ORDER BY tablename, indexname;

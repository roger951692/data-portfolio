-- ============================================================
-- E-Commerce SQL Analysis — Portfolio Queries
-- Author : Roger Amorín Suñé
-- Stack  : PostgreSQL 14+ (compatible with most modern dialects)
-- Run    : psql -U postgres -d portfolio -f schema.sql
--          psql -U postgres -d portfolio -f seed_data.sql
--          psql -U postgres -d portfolio -f queries.sql
-- ============================================================
--
-- The 10 queries below answer recurring business questions for
-- a small e-commerce shop (revenue trends, customer LTV, cohort
-- retention, RFM segmentation, data quality, performance tuning).
-- Each block states the business goal, the technical concepts
-- used, and what to expect in the output.
--
-- ============================================================


-- ============================================================
-- QUERY 01 · Monthly Revenue Trend
-- Business goal : Track monthly gross revenue from completed orders
--                 and how the average order value evolves.
-- Concepts      : DATE_TRUNC, GROUP BY, aggregation, ORDER BY
-- Output cols   : month · total_orders · gross_revenue · avg_order_value
-- ============================================================

SELECT
    DATE_TRUNC('month', p.payment_date)        AS month,
    COUNT(DISTINCT o.order_id)                 AS total_orders,
    ROUND(SUM(oi.quantity * oi.unit_price), 2) AS gross_revenue,
    ROUND(AVG(oi.quantity * oi.unit_price), 2) AS avg_order_value
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
JOIN payments p     ON o.order_id = p.order_id
WHERE o.status = 'completed'
GROUP BY DATE_TRUNC('month', p.payment_date)
ORDER BY month;


-- ============================================================
-- QUERY 02 · Top 10 Products by Gross Margin (€)
-- Business goal : Identify the most profitable products in absolute
--                 terms (revenue minus cost), and their margin %.
-- Concepts      : JOIN, calculated fields, NULLIF safety, ORDER BY, LIMIT
-- Output cols   : product_id · product_name · category · units_sold ·
--                 total_revenue · total_cost · gross_margin · margin_pct
-- ============================================================

SELECT
    p.product_id,
    p.name                                                AS product_name,
    p.category,
    SUM(oi.quantity)                                      AS units_sold,
    ROUND(SUM(oi.quantity * oi.unit_price), 2)            AS total_revenue,
    ROUND(SUM(oi.quantity * p.cost_price), 2)             AS total_cost,
    ROUND(SUM(oi.quantity * (oi.unit_price - p.cost_price)), 2)
                                                          AS gross_margin,
    ROUND(
        100.0 * SUM(oi.quantity * (oi.unit_price - p.cost_price))
        / NULLIF(SUM(oi.quantity * oi.unit_price), 0),
    1)                                                    AS margin_pct
FROM products p
JOIN order_items oi ON p.product_id = oi.product_id
JOIN orders o       ON oi.order_id  = o.order_id
WHERE o.status = 'completed'
GROUP BY p.product_id, p.name, p.category
ORDER BY gross_margin DESC
LIMIT 10;


-- ============================================================
-- QUERY 03 · Customer Lifetime Value (LTV)
-- Business goal : Rank customers by total spend and identify the
--                 top buyers and their typical order size.
-- Concepts      : CTE, JOIN, aggregation, RANK window function
-- Output cols   : customer info · total_orders · lifetime_value ·
--                 first_order · last_order · ltv_rank · avg_order_value
-- ============================================================

WITH customer_spend AS (
    SELECT
        c.customer_id,
        c.name,
        c.city,
        c.signup_date,
        COUNT(DISTINCT o.order_id)               AS total_orders,
        ROUND(SUM(oi.quantity * oi.unit_price), 2)
                                                 AS lifetime_value,
        MIN(o.order_date)                        AS first_order,
        MAX(o.order_date)                        AS last_order
    FROM customers c
    JOIN orders o       ON c.customer_id = o.customer_id
    JOIN order_items oi ON o.order_id    = oi.order_id
    WHERE o.status = 'completed'
    GROUP BY c.customer_id, c.name, c.city, c.signup_date
)
SELECT
    *,
    RANK() OVER (ORDER BY lifetime_value DESC)       AS ltv_rank,
    ROUND(lifetime_value / total_orders, 2)          AS avg_order_value
FROM customer_spend
ORDER BY ltv_rank;


-- ============================================================
-- QUERY 04 · Cohort Retention Analysis
-- Business goal : For each signup cohort (month), how many customers
--                 placed orders in subsequent months? Reveals how
--                 well the shop retains buyers over time.
-- Concepts      : CTEs, DATE_TRUNC, AGE() / month diff, ratio
-- Note          : The previous version used
--                 EXTRACT(MONTH FROM AGE(...)) which returns ONLY
--                 the month component (so 13 months ≡ 1). The fix
--                 below adds 12 × the year component to get the
--                 true number of months between cohort and order.
-- Output cols   : cohort_month · months_since_signup · active_customers ·
--                 cohort_size · retention_pct
-- ============================================================

WITH cohorts AS (
    SELECT
        c.customer_id,
        DATE_TRUNC('month', c.signup_date) AS cohort_month,
        DATE_TRUNC('month', o.order_date)  AS order_month
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
        cohort_month,
        order_month,
        COUNT(DISTINCT customer_id) AS active_customers,
        -- months_since_signup: full months between cohort and order
        (EXTRACT(YEAR  FROM AGE(order_month, cohort_month)) * 12
       +  EXTRACT(MONTH FROM AGE(order_month, cohort_month)))::INT
                                       AS months_since_signup
    FROM cohorts
    GROUP BY cohort_month, order_month
)
SELECT
    r.cohort_month,
    r.months_since_signup,
    r.active_customers,
    cs.cohort_size,
    ROUND(100.0 * r.active_customers / cs.cohort_size, 1)
                                       AS retention_pct
FROM retention r
JOIN cohort_sizes cs ON r.cohort_month = cs.cohort_month
ORDER BY r.cohort_month, r.months_since_signup;


-- ============================================================
-- QUERY 05 · RFM Customer Segmentation
-- Business goal : Score every customer on Recency, Frequency,
--                 Monetary value (3 buckets each → 27 cells) and
--                 group them into 5 actionable segments.
-- Concepts      : CTEs, NTILE, CASE, composite scoring
-- Output cols   : customer info · r_score · f_score · m_score ·
--                 rfm_total · segment
-- ============================================================

WITH rfm_raw AS (
    SELECT
        c.customer_id,
        c.name,
        MAX(o.order_date)                AS last_order_date,
        COUNT(DISTINCT o.order_id)       AS frequency,
        SUM(oi.quantity * oi.unit_price) AS monetary
    FROM customers c
    JOIN orders o       ON c.customer_id = o.customer_id
    JOIN order_items oi ON o.order_id    = oi.order_id
    WHERE o.status = 'completed'
    GROUP BY c.customer_id, c.name
),
rfm_scores AS (
    SELECT
        *,
        NTILE(3) OVER (ORDER BY last_order_date DESC) AS r_score, -- 3 = most recent
        NTILE(3) OVER (ORDER BY frequency       DESC) AS f_score,
        NTILE(3) OVER (ORDER BY monetary        DESC) AS m_score
    FROM rfm_raw
)
SELECT
    customer_id,
    name,
    last_order_date,
    frequency,
    ROUND(monetary, 2)              AS monetary,
    r_score, f_score, m_score,
    (r_score + f_score + m_score)   AS rfm_total,
    CASE
        WHEN (r_score + f_score + m_score) >= 8           THEN 'Champions'
        WHEN (r_score + f_score + m_score) >= 6           THEN 'Loyal Customers'
        WHEN r_score = 3 AND (f_score + m_score) <= 3     THEN 'New Customers'
        WHEN r_score <= 2 AND f_score >= 2                THEN 'At Risk'
        ELSE 'Need Attention'
    END                              AS segment
FROM rfm_scores
ORDER BY rfm_total DESC;


-- ============================================================
-- QUERY 06 · First-Time vs Repeat Purchase
-- Business goal : Flag every order as first-time or repeat and
--                 compute days between consecutive orders to
--                 estimate the natural buying cadence.
-- Concepts      : ROW_NUMBER, LAG window functions
-- Output cols   : order info · order_rank · purchase_type ·
--                 previous_order_date · days_since_last_order
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
    CASE WHEN order_rank = 1
         THEN 'First Purchase'
         ELSE 'Repeat Purchase'
    END                                 AS purchase_type,
    previous_order_date,
    (order_date - previous_order_date)  AS days_since_last_order
FROM ranked_orders
ORDER BY customer_id, order_rank;


-- ============================================================
-- QUERY 07 · Year-over-Year Revenue by Category
-- Business goal : Compare 2022 vs 2023 revenue per category and
--                 surface YoY growth rate.
-- Concepts      : DATE_PART, conditional aggregation (FILTER), ratio
-- Output cols   : category · revenue_2022 · revenue_2023 · yoy_growth_pct
-- ============================================================

SELECT
    p.category,
    ROUND(SUM(oi.quantity * oi.unit_price)
        FILTER (WHERE DATE_PART('year', o.order_date) = 2022), 2) AS revenue_2022,
    ROUND(SUM(oi.quantity * oi.unit_price)
        FILTER (WHERE DATE_PART('year', o.order_date) = 2023), 2) AS revenue_2023,
    ROUND(
        100.0 * (
            SUM(oi.quantity * oi.unit_price)
                FILTER (WHERE DATE_PART('year', o.order_date) = 2023)
            - SUM(oi.quantity * oi.unit_price)
                FILTER (WHERE DATE_PART('year', o.order_date) = 2022)
        ) / NULLIF(
            SUM(oi.quantity * oi.unit_price)
                FILTER (WHERE DATE_PART('year', o.order_date) = 2022)
        , 0),
    1)                                                            AS yoy_growth_pct
FROM products p
JOIN order_items oi ON p.product_id = oi.product_id
JOIN orders o       ON oi.order_id  = o.order_id
WHERE o.status = 'completed'
GROUP BY p.category
ORDER BY revenue_2023 DESC NULLS LAST;


-- ============================================================
-- QUERY 08 · Data Quality — Active Orders Without Payment
-- Business goal : Find orders flagged as completed (or pending)
--                 that have no row in payments. These are
--                 reconciliation candidates the finance team
--                 should review.
-- Concepts      : LEFT JOIN, IS NULL (anti-join pattern)
-- Output cols   : order info · customer info · order_total
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
WHERE p.payment_id IS NULL                       -- no payment found
  AND o.status NOT IN ('cancelled', 'refunded')  -- exclude expected-no-payment cases
GROUP BY o.order_id, o.customer_id, c.name, o.order_date, o.status
ORDER BY o.order_date;


-- ============================================================
-- QUERY 09 · Running Total Revenue + 7-Day Rolling Average
-- Business goal : Daily revenue, cumulative revenue and a smoothed
--                 7-day rolling average — exactly the shape a
--                 cash-flow chart needs.
-- Concepts      : SUM/AVG OVER, frame clauses (ROWS BETWEEN ...)
-- Output cols   : day · daily_revenue · running_total · rolling_7day_avg
-- ============================================================

WITH daily_revenue AS (
    SELECT
        p.payment_date  AS day,
        SUM(p.amount)   AS daily_revenue
    FROM payments p
    JOIN orders o ON p.order_id = o.order_id
    WHERE o.status = 'completed'
    GROUP BY p.payment_date
)
SELECT
    day,
    ROUND(daily_revenue, 2)               AS daily_revenue,
    ROUND(SUM(daily_revenue) OVER (
        ORDER BY day
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ), 2)                                 AS running_total,
    ROUND(AVG(daily_revenue) OVER (
        ORDER BY day
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 2)                                 AS rolling_7day_avg
FROM daily_revenue
ORDER BY day;


-- ============================================================
-- QUERY 10 · Performance — Index Strategy Demo
-- Business goal : Show that an index on orders(order_date) lets
--                 PostgreSQL do an Index Scan instead of a Seq Scan
--                 when filtering by date range. Educational query.
-- Concepts      : EXPLAIN ANALYZE, query plans, idx selection
-- ============================================================

-- Step 1 — Inspect the plan for a date-bounded query.
EXPLAIN ANALYZE
SELECT
    o.order_id,
    o.order_date,
    c.name,
    SUM(oi.quantity * oi.unit_price) AS order_total
FROM orders o
JOIN customers c    ON o.customer_id = c.customer_id
JOIN order_items oi ON o.order_id    = oi.order_id
WHERE o.order_date BETWEEN '2023-01-01' AND '2023-06-30'
  AND o.status = 'completed'
GROUP BY o.order_id, o.order_date, c.name
ORDER BY order_total DESC;
-- Expected: with idx_orders_date defined in schema.sql the planner
-- chooses an Index Scan / Bitmap Index Scan on orders.order_date.
-- On a tiny table like this seed data PostgreSQL may still pick a
-- Seq Scan because the table fits in a single page; the index is
-- only worth it once the table grows.

-- Step 2 — Inspect indexes that exist on the analytics tables.
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('orders', 'order_items', 'payments')
ORDER BY tablename, indexname;

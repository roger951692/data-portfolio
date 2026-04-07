# E-Commerce SQL Analysis

Advanced SQL queries on a simulated e-commerce database covering orders, customers, products and payments.

## Database Schema

```
customers       (customer_id, name, city, signup_date)
orders          (order_id, customer_id, order_date, status)
order_items     (item_id, order_id, product_id, quantity, unit_price)
products        (product_id, name, category, cost_price)
payments        (payment_id, order_id, amount, payment_date, method)
```

## Queries

| # | Topic | Concepts |
|---|---|---|
| 01 | Monthly revenue trend | GROUP BY, DATE_TRUNC, aggregation |
| 02 | Top 10 products by margin | JOIN, calculated fields |
| 03 | Customer lifetime value (LTV) | CTE, aggregation |
| 04 | Cohort retention analysis | Window functions, self-JOIN |
| 05 | RFM customer segmentation | NTILE, CASE, CTEs |
| 06 | First vs repeat purchase rate | LAG, ROW_NUMBER |
| 07 | Revenue by category (YoY) | DATE_PART, conditional aggregation |
| 08 | Orders with no payment (data quality) | LEFT JOIN, IS NULL |
| 09 | Running total revenue | SUM OVER, ORDER BY |
| 10 | Query optimization with indexes | EXPLAIN ANALYZE, index strategy |

## How to run

All queries are PostgreSQL-compatible. Load the schema + seed data:

```bash
psql -U postgres -d portfolio -f schema.sql
psql -U postgres -d portfolio -f seed_data.sql
psql -U postgres -d portfolio -f queries.sql
```

Or run individual queries in any PostgreSQL-compatible environment (DBeaver, pgAdmin, supabase, etc.)

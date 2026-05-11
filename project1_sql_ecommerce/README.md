# Project 1 · E-Commerce SQL Analysis

Advanced SQL analysis of a small e-commerce shop. Ten queries answer recurring business questions a junior data analyst would meet on day one — revenue trends, customer LTV, cohort retention, RFM segmentation, data quality, and query performance.

The schema models the shop with five related tables (customers, products, orders, order_items, payments) and the seed data spans 2022–2023 so the queries return time-series results suitable for charting.

## What's inside

| File | Purpose |
|---|---|
| `schema.sql` | DDL — 5 tables, FKs, CHECK constraints, indexes |
| `seed_data.sql` | Sample data (20 customers, 15 products, 35 orders, 31 payments) |
| `queries.sql` | The 10 analytical queries (PostgreSQL dialect) |
| `run_queries.py` | Self-contained runner that builds an SQLite DB and executes every query, saving CSV results and charts |
| `sample_outputs/` | Pre-generated CSV results and PNG charts (so the project is readable without running anything) |

## The ten queries at a glance

| # | Topic | Concepts | Business question |
|---|---|---|---|
| 01 | Monthly revenue trend | `DATE_TRUNC`, aggregation | How does revenue evolve month over month? |
| 02 | Top 10 products by gross margin | JOIN, calculated fields | Which products drive the most profit? |
| 03 | Customer Lifetime Value | CTE, `RANK()` | Who are the best customers? |
| 04 | Cohort retention | CTEs, `AGE()`, ratios | Do new customers come back? When? |
| 05 | RFM segmentation | `NTILE`, `CASE`, composite scoring | Where to focus marketing spend? |
| 06 | First-time vs repeat purchase | `ROW_NUMBER`, `LAG` | What's the natural buying cadence? |
| 07 | YoY revenue by category | `FILTER`, conditional agg | Which categories are growing? |
| 08 | Data quality — orders without payment | `LEFT JOIN ... IS NULL` | Are there reconciliation gaps? |
| 09 | Running total + 7-day rolling average | `SUM OVER`, `AVG OVER`, frame clauses | What does the cash-flow curve look like? |
| 10 | Query performance — index strategy | `EXPLAIN ANALYZE`, plan reading | Is the query using the right index? |

## How to run

### Option 1 — PostgreSQL (recommended for the original queries)

```bash
psql -U postgres -d portfolio -f schema.sql
psql -U postgres -d portfolio -f seed_data.sql
psql -U postgres -d portfolio -f queries.sql
```

Or open the files in any PostgreSQL-compatible client (DBeaver, pgAdmin, Supabase…).

### Option 2 — Zero-install with SQLite + Python

```bash
pip install -r ../requirements.txt
python run_queries.py
```

This builds an SQLite database in memory, runs every query, prints a summary, and saves the full results plus charts under `sample_outputs/`. No PostgreSQL, no Docker — just Python.

### Option 3 — Just look at the outputs

If you only want to read the analysis, jump straight to [`sample_outputs/`](./sample_outputs/) — every query has its CSV result and (where it makes sense) a chart.

## Highlights worth noting

- **The cohort retention query (Q4)** uses `AGE()` with both year and month components, which is the correct way to compute month-difference across year boundaries (a common bug is to extract only the month part).
- **The data-quality query (Q8)** is intentionally calibrated against the seed data: order #34 has no payment row and `status = 'completed'`, so it surfaces as a real anomaly worth investigating.
- **The RFM query (Q5)** uses `NTILE(3)` and a composite score 3-9 to derive five actionable segments (Champions, Loyal, New, At Risk, Need Attention).
- **The performance query (Q10)** is honest about scale: on this seed data PostgreSQL may still pick a `Seq Scan` because the table fits in a single page. The educational point is the index strategy and how to read execution plans.

## Stack

PostgreSQL 14+ for the canonical queries. Python 3.10 + `sqlite3` + Pandas + Matplotlib for the runnable demo. No external dependencies beyond the standard data-analysis trio.

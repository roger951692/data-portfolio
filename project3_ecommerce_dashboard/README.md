# Project 3 · E-Commerce Analytics Dashboard

End-to-end analytics on a real-world Brazilian e-commerce dataset (~100 K orders, 2016–2018) — from raw CSVs through SQL data preparation and Python feature engineering to an interactive Power BI dashboard.

The project is built around the public **Brazilian E-Commerce Public Dataset by Olist**, available on Kaggle. The same pipeline runs on a small synthetic equivalent that ships with the repo, so the project is fully reproducible even before downloading the real dataset.

## Story

We're a small e-commerce shop. Three questions land on the desk on day one of the new analytics function:

1. **Where does revenue come from?** Which categories, regions, sellers and customer segments?
2. **Are customers coming back?** What does the cohort-retention picture look like, and how is it changing over time?
3. **What hurts conversion?** Where do we see logistics delays, low review scores, or payment friction — and how do those correlate with revenue and repeat-purchase rate?

The notebook and dashboard below answer them with an analyst's toolkit: SQL for the data prep, Python (Pandas) for feature engineering, Power BI for the executive view.

## Layout

```
project3_ecommerce_dashboard/
├── README.md                       (this file)
├── requirements.txt
├── data/
│   ├── raw/                        ← Olist CSVs go here (download instructions below)
│   └── processed/                  ← outputs from the ETL step
├── sql/
│   ├── 00_create_schema.sql        DDL for an SQLite/PostgreSQL warehouse
│   ├── 10_load_raw.sql             COPY/IMPORT statements (Postgres) + Python loader
│   ├── 20_revenue_by_category.sql
│   ├── 21_revenue_by_state.sql
│   ├── 22_cohort_retention.sql
│   ├── 23_logistics_review.sql
│   ├── 24_top_sellers.sql
│   └── 25_payment_methods.sql
├── notebooks/
│   ├── 01_etl_and_features.ipynb   Loads raw, cleans, builds the analytical tables
│   └── 02_eda_and_kpis.ipynb       Computes the 12 KPIs powering the dashboard
├── powerbi/
│   ├── dashboard_spec.md           5-page dashboard specification with wireframes
│   └── pbix_data/                  Pre-aggregated CSVs ready to import into Power BI
└── outputs/
    ├── kpi_summary.png             Executive KPI card preview
    ├── retention_heatmap.png       Cohort retention chart preview
    └── ...
```

## How to set it up

### Option 1 — Run with synthetic data (fastest)

```bash
pip install -r requirements.txt
python scripts/build_synthetic.py     # generates 5 K-row Olist-shaped CSVs in data/raw/
jupyter notebook notebooks/01_etl_and_features.ipynb
```

The synthetic generator preserves the Olist schema exactly (9 tables, identical column names) so every SQL query and notebook cell runs identically against synthetic and real data.

### Option 2 — Run with the real Olist dataset (recommended)

1. Download the dataset from Kaggle:
   <https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce>
2. Unzip the CSVs into `data/raw/` (keep the original filenames):
   - `olist_customers_dataset.csv`
   - `olist_geolocation_dataset.csv`
   - `olist_order_items_dataset.csv`
   - `olist_order_payments_dataset.csv`
   - `olist_order_reviews_dataset.csv`
   - `olist_orders_dataset.csv`
   - `olist_products_dataset.csv`
   - `olist_sellers_dataset.csv`
   - `product_category_name_translation.csv`
3. Run the same notebooks. The pipeline will pick up real data automatically.

### Option 3 — Just look at the dashboard

The `powerbi/dashboard_spec.md` document is a 5-page wireframe of the final dashboard with annotated mockups for each visual. Pre-aggregated CSVs ready to import live in `powerbi/pbix_data/`.

## The 12 KPIs that power the dashboard

| # | KPI | How it's computed |
|---|---|---|
| 1 | Total revenue | `SUM(payment_value)` over delivered orders |
| 2 | Orders | `COUNT(DISTINCT order_id)` |
| 3 | Avg order value | revenue ÷ orders |
| 4 | Avg items per order | total items ÷ orders |
| 5 | Repeat-customer rate | customers with ≥2 orders ÷ total customers |
| 6 | Avg delivery delay (days) | actual − estimated delivery time |
| 7 | Late-delivery share | % of orders delivered after the estimated date |
| 8 | Avg review score | mean of `review_score` (1–5) |
| 9 | % low-review (1–2) | low-score reviews ÷ total reviews |
| 10 | Top category share | revenue of largest category ÷ total revenue |
| 11 | Top state share | revenue of largest state ÷ total revenue |
| 12 | Payment-mix entropy | Shannon entropy across payment methods |

## Stack

- **SQL** — SQLite for portability, with a Postgres-compatible variant in `sql/`. Joins, aggregations, window functions, cohort math.
- **Python** — Pandas + NumPy for feature engineering, Matplotlib for the preview charts that go into the README.
- **Power BI** — final dashboard. The `dashboard_spec.md` file describes every page in detail: visuals, fields, filters, slicers, drill-throughs, and the colour palette.

## Status

This project is in active development. The README, schema documentation, SQL queries, ETL notebook structure and Power BI specification are in place. Real-data integration is the next milestone (pending the dataset download on the local machine).

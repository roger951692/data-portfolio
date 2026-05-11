# Power BI Dashboard — Build Specification

A 5-page interactive Power BI report on the Olist Brazilian E-Commerce dataset. Every page below is described with its visuals, the fields they bind to, the filters/slicers and the interactions. Build them in this order — each page reuses fields and the data model from the previous one.

## Data model (build first)

Import these tables from `powerbi/pbix_data/` (or load straight from the staging tables produced by `notebooks/01_etl_and_features.ipynb`):

| Table | Grain | Key fields |
|---|---|---|
| `dim_date` | one row per day | `date`, `year`, `quarter`, `month`, `month_label`, `weekday` |
| `dim_customer` | one row per customer | `customer_id`, `customer_state`, `customer_city` |
| `dim_product` | one row per product | `product_id`, `category_en`, `weight_g`, `volume_cm3` |
| `dim_seller` | one row per seller | `seller_id`, `seller_state`, `seller_city` |
| `fact_orders` | one row per order | `order_id`, `customer_id`, `order_purchase_ts`, `delivered_ts`, `estimated_ts`, `review_score`, `total_items`, `revenue`, `freight`, `is_late`, `delivery_delay_days` |
| `fact_order_items` | one row per item | `order_id`, `product_id`, `seller_id`, `price`, `freight_value` |
| `fact_payments` | one row per payment installment | `order_id`, `payment_type`, `payment_installments`, `payment_value` |

**Relationships** (single direction, * → 1):

- `fact_orders[customer_id]` → `dim_customer[customer_id]`
- `fact_orders[order_purchase_ts]` (truncated to date) → `dim_date[date]`
- `fact_order_items[order_id]` → `fact_orders[order_id]`
- `fact_order_items[product_id]` → `dim_product[product_id]`
- `fact_order_items[seller_id]` → `dim_seller[seller_id]`
- `fact_payments[order_id]` → `fact_orders[order_id]`

Mark `dim_date` as a date table.

## Measures (DAX) — define once, reuse everywhere

```dax
Total Revenue       := SUM(fact_orders[revenue])
Orders              := DISTINCTCOUNT(fact_orders[order_id])
Avg Order Value     := DIVIDE([Total Revenue], [Orders])
Total Items         := SUM(fact_orders[total_items])
Avg Items per Order := DIVIDE([Total Items], [Orders])

Customers           := DISTINCTCOUNT(fact_orders[customer_id])
Repeat Customers    :=
    CALCULATE(
        DISTINCTCOUNT(fact_orders[customer_id]),
        FILTER(
            VALUES(fact_orders[customer_id]),
            CALCULATE(DISTINCTCOUNT(fact_orders[order_id])) >= 2
        )
    )
Repeat Rate %       := DIVIDE([Repeat Customers], [Customers]) * 100

Avg Delivery Delay  := AVERAGE(fact_orders[delivery_delay_days])
Late Orders         := CALCULATE([Orders], fact_orders[is_late] = TRUE)
Late Share %        := DIVIDE([Late Orders], [Orders]) * 100

Avg Review Score    := AVERAGE(fact_orders[review_score])
Low Review Orders   := CALCULATE([Orders], fact_orders[review_score] <= 2)
Low Review Share %  := DIVIDE([Low Review Orders], [Orders]) * 100

Revenue PY          := CALCULATE([Total Revenue], DATEADD(dim_date[date], -1, YEAR))
Revenue YoY %       := DIVIDE([Total Revenue] - [Revenue PY], [Revenue PY]) * 100
```

## Global theme

- **Palette** — primary `#3a86ff` (blue), secondary `#fb5607` (orange), accent `#06d6a0` (green), neutral `#073b4c` (dark) and `#eef2f5` (light gray background).
- **Font** — Segoe UI, 11pt body, 14pt subtitles, 18pt KPI numbers.
- **Card backgrounds** — `#ffffff` with 8px corner radius and a subtle `#dfe6ec` border.
- **Page background** — `#eef2f5`.
- **Filters pane** — collapsed by default. Slicers live on each page top bar.

## Global slicers (sync across pages)

- **Year** — single-select slicer at the top right of every page (sync all pages).
- **State** — multi-select horizontal slicer on Pages 2 and 4.
- **Category** — multi-select horizontal slicer on Pages 1 and 5.

---

# Page 1 · Executive Overview

The "30-second" page. A C-level should leave it knowing how the business performed and where the next problem is hiding.

## Layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Title:  E-Commerce Performance · 2016-2018      Year [▾]  Category [▾] │
├──────────────────────────────────────────────────────────────────────────┤
│ ┌─KPI─┐  ┌─KPI─┐  ┌─KPI─┐  ┌─KPI─┐  ┌─KPI─┐  ┌─KPI─┐                    │
│ │ Rev │  │ Ord │  │ AOV │  │ Cus │  │ Rep │  │ ★   │                    │
│ └─────┘  └─────┘  └─────┘  └─────┘  └─────┘  └─────┘                    │
├──────────────────────────────────────────────────────────────────────────┤
│ Monthly revenue (line + 3M rolling avg)        Top 8 categories (bars)   │
│ ┌────────────────────────────────┐  ┌────────────────────────────────┐  │
│ │                                │  │                                │  │
│ │                                │  │                                │  │
│ └────────────────────────────────┘  └────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────────────┤
│ Brazil map · revenue by state            Order status mix (donut)        │
│ ┌────────────────────────────────┐  ┌────────────────────────────────┐  │
│ │                                │  │                                │  │
│ └────────────────────────────────┘  └────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

## Visuals

| # | Visual | Fields |
|---|---|---|
| 1 | **Revenue** card | `[Total Revenue]` · subtitle `[Revenue YoY %]` (green ↑ / red ↓) |
| 2 | **Orders** card | `[Orders]` |
| 3 | **AOV** card | `[Avg Order Value]` |
| 4 | **Customers** card | `[Customers]` |
| 5 | **Repeat-rate** card | `[Repeat Rate %]` (target line at 5 %, conditional formatting) |
| 6 | **Avg review** card | `[Avg Review Score]` (1–5 stars icon + value) |
| 7 | **Monthly revenue** line chart | X: `dim_date[month_label]` · Y1: `[Total Revenue]` · Y2: 3-month rolling via DAX or in-visual analytics |
| 8 | **Top 8 categories** bar chart | Y: `dim_product[category_en]` (Top N filter = 8 by `[Total Revenue]`) · X: `[Total Revenue]` · data label on |
| 9 | **Brazil state map** filled map | Location: `dim_customer[customer_state]` · Bubble size: `[Total Revenue]` · Tooltip: orders, AOV |
| 10 | **Order-status donut** | Legend: `fact_orders[order_status]` · Values: `[Orders]` |

## Interactions
- Click on a category bar (visual 8) cross-filters all other visuals on the page.
- Click on a state in the map (visual 9) cross-filters everything except itself.
- Cards 1-6 *do not* react to cross-filtering (set "Edit interactions" → "None"); they should always show the slicer-level total.

---

# Page 2 · Customer Cohorts

How the cohort mix matures over time and where retention drops.

## Visuals

| # | Visual | Fields | Notes |
|---|---|---|---|
| 1 | **Cohort retention heatmap** matrix | Rows: `cohort_month` · Cols: `months_since_signup` (0..18) · Values: retention % | Conditional formatting: gradient `#fff5e6` → `#fb5607` |
| 2 | **New vs returning customers** stacked column | X: `dim_date[month_label]` · Y: `[Customers]` split by `is_new` | `is_new` is a calculated column on `fact_orders` |
| 3 | **Avg orders per customer** line | X: `dim_date[month_label]` · Y: `DIVIDE([Orders], [Customers])` |
| 4 | **Top 20 customers by lifetime value** table | `customer_id`, `customer_state`, total orders, total revenue, first/last order, days active |

Slicer: `dim_customer[customer_state]` (multi-select).

---

# Page 3 · Product & Category

Which products and categories drive volume, revenue and margin (where possible).

## Visuals

| # | Visual | Fields |
|---|---|---|
| 1 | **Category revenue Pareto** | X: category, Y left: revenue (bars), Y right: cumulative % (line) — Top 20 categories |
| 2 | **Avg ticket per category** lollipop / dot plot | X: `[Avg Order Value]` per category |
| 3 | **Product-quality scatter** | X: avg review score · Y: total revenue · size: orders · colour: category |
| 4 | **Top 10 products** table | product_id, category, units sold, revenue, avg review |

Drill-through from page 1 category bar → page 3 (filtered to that category).

---

# Page 4 · Logistics & Reviews

Where late deliveries and low reviews are concentrated.

## Visuals

| # | Visual | Fields |
|---|---|---|
| 1 | **Avg delivery delay by state** map | Location: `customer_state` · Color saturation: `[Avg Delivery Delay]` |
| 2 | **Late share by state** column chart | X: `customer_state` (top 15) · Y: `[Late Share %]` · target line at 7 % |
| 3 | **Review score distribution** column | X: `review_score` (1..5) · Y: count of reviews |
| 4 | **Late vs on-time review impact** | Two cards side-by-side: avg review score for late orders vs on-time |
| 5 | **Top 10 routes** matrix | Rows: seller_state → customer_state · Values: orders, avg delay |

---

# Page 5 · Payments

Payment-method mix and its relationship with order value and on-time rate.

## Visuals

| # | Visual | Fields |
|---|---|---|
| 1 | **Payment method share** donut | Legend: `payment_type` · Values: `[Orders]` |
| 2 | **Installments distribution** column | X: payment_installments · Y: orders · facet by payment_type |
| 3 | **AOV by payment method** bar | X: `[Avg Order Value]` per method |
| 4 | **Heatmap: method × month** | Rows: payment_type · Cols: `month_label` · Values: revenue |

---

# Build checklist

- [ ] Import the seven tables from `powerbi/pbix_data/`
- [ ] Mark `dim_date` as date table
- [ ] Define the 14 DAX measures listed above
- [ ] Apply theme colours (palette + fonts)
- [ ] Page 1 — Executive overview (10 visuals)
- [ ] Page 2 — Cohorts (4 visuals + slicer)
- [ ] Page 3 — Product & Category (4 visuals + drill-through)
- [ ] Page 4 — Logistics & Reviews (5 visuals)
- [ ] Page 5 — Payments (4 visuals)
- [ ] Sync slicers across pages (Year, State, Category)
- [ ] Configure tooltips on the Brazil map (orders, AOV)
- [ ] Publish to Power BI Service or export to PDF and add a screenshot to `outputs/`

When the report is published, paste a screenshot of Page 1 into `outputs/dashboard_overview.png` and link it from the project README.

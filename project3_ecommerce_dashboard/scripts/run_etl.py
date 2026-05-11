"""
ETL pipeline — raw Olist CSVs → analytical tables → Power BI inputs.

Reads CSVs from ``data/raw/``, builds the star-schema tables described
in ``sql/00_create_schema.sql`` and writes them as CSVs under
``powerbi/pbix_data/`` ready to import into Power BI.

Also generates two preview PNGs into ``outputs/`` so the README has a
visual sample of the analysis.

Run with::

    python scripts/run_etl.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT_DATA = ROOT / "powerbi" / "pbix_data"
OUT_FIGS = ROOT / "outputs"
OUT_DATA.mkdir(parents=True, exist_ok=True)
OUT_FIGS.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({"figure.dpi": 110, "font.size": 11,
                     "axes.spines.top": False, "axes.spines.right": False})


# ---------------------------------------------------------------------------
# 1. Load raw
# ---------------------------------------------------------------------------

def load_raw():
    print("Loading raw CSVs...")
    customers = pd.read_csv(RAW / "olist_customers_dataset.csv")
    sellers   = pd.read_csv(RAW / "olist_sellers_dataset.csv")
    products  = pd.read_csv(RAW / "olist_products_dataset.csv")
    orders    = pd.read_csv(RAW / "olist_orders_dataset.csv",
                            parse_dates=["order_purchase_timestamp",
                                         "order_approved_at",
                                         "order_delivered_carrier_date",
                                         "order_delivered_customer_date",
                                         "order_estimated_delivery_date"])
    items     = pd.read_csv(RAW / "olist_order_items_dataset.csv")
    payments  = pd.read_csv(RAW / "olist_order_payments_dataset.csv")
    reviews   = pd.read_csv(RAW / "olist_order_reviews_dataset.csv")
    cat       = pd.read_csv(RAW / "product_category_name_translation.csv")
    print(f"  customers={len(customers):,} orders={len(orders):,} "
          f"items={len(items):,} payments={len(payments):,} "
          f"reviews={len(reviews):,}")
    return customers, sellers, products, orders, items, payments, reviews, cat


# ---------------------------------------------------------------------------
# 2. Build dimensions
# ---------------------------------------------------------------------------

def build_dimensions(customers, sellers, products, orders, cat):
    # dim_date — one row per day in the order span
    dmin = orders["order_purchase_timestamp"].min().normalize()
    dmax = orders["order_purchase_timestamp"].max().normalize()
    dates = pd.date_range(dmin, dmax, freq="D")
    dim_date = pd.DataFrame({"date": dates})
    dim_date["year"]         = dim_date["date"].dt.year
    dim_date["quarter"]      = dim_date["date"].dt.quarter
    dim_date["month"]        = dim_date["date"].dt.month
    dim_date["month_label"]  = dim_date["date"].dt.to_period("M").astype(str)
    dim_date["weekday"]      = dim_date["date"].dt.weekday
    dim_date["weekday_name"] = dim_date["date"].dt.day_name()
    dim_date["is_weekend"]   = (dim_date["weekday"] >= 5).astype(int)

    # cohort_month per customer = first order month
    first_order = (orders.merge(customers, on="customer_id")
                   .groupby("customer_id")["order_purchase_timestamp"].min()
                   .dt.to_period("M").astype(str)
                   .rename("cohort_month").reset_index())
    dim_customer = (customers.merge(first_order, on="customer_id", how="left")
                    [["customer_id", "customer_state",
                      "customer_city", "cohort_month"]])

    # Translate category, fold weight × volume
    products = products.merge(cat, on="product_category_name", how="left")
    products["volume_cm3"] = (products["product_length_cm"]
                              * products["product_height_cm"]
                              * products["product_width_cm"])
    dim_product = (products.rename(columns={
        "product_category_name":         "category",
        "product_category_name_english": "category_en",
        "product_weight_g":              "weight_g",
        "product_photos_qty":            "photos_qty",
    })[["product_id", "category", "category_en",
        "weight_g", "volume_cm3", "photos_qty"]])

    dim_seller = sellers[["seller_id", "seller_state", "seller_city"]]

    return dim_date, dim_customer, dim_product, dim_seller


# ---------------------------------------------------------------------------
# 3. Build facts
# ---------------------------------------------------------------------------

def build_facts(orders, items, payments, reviews):
    # Aggregate items → revenue, total_items, freight per order
    item_agg = items.groupby("order_id").agg(
        total_items=("order_item_id", "count"),
        revenue=("price", "sum"),
        freight=("freight_value", "sum"),
    ).reset_index()
    item_agg["revenue"] = item_agg["revenue"] + item_agg["freight"]

    # Aggregate payments → number of methods + max installments
    pay_agg = payments.groupby("order_id").agg(
        payment_methods=("payment_type", "nunique"),
        payment_installments=("payment_installments", "max"),
    ).reset_index()

    # Reviews → take latest if multiple
    rev_agg = (reviews.sort_values("review_creation_date")
               .groupby("order_id")["review_score"].last().reset_index())

    fact_orders = (orders.merge(item_agg, on="order_id", how="left")
                         .merge(pay_agg, on="order_id", how="left")
                         .merge(rev_agg, on="order_id", how="left"))

    # Delivery delay (positive = late)
    fact_orders["delivery_delay_days"] = (
        (fact_orders["order_delivered_customer_date"]
         - fact_orders["order_estimated_delivery_date"]).dt.days
    )
    fact_orders["is_late"] = (fact_orders["delivery_delay_days"] > 0).astype("Int64")

    fact_orders = fact_orders.rename(columns={
        "order_purchase_timestamp":     "order_purchase_ts",
        "order_delivered_customer_date": "delivered_ts",
        "order_estimated_delivery_date": "estimated_ts",
    })[["order_id", "customer_id", "order_status",
        "order_purchase_ts", "delivered_ts", "estimated_ts",
        "delivery_delay_days", "is_late",
        "review_score", "total_items", "revenue", "freight",
        "payment_methods", "payment_installments"]]

    fact_order_items = items[["order_id", "order_item_id", "product_id",
                              "seller_id", "price", "freight_value"]]
    fact_payments    = payments[["order_id", "payment_sequential",
                                 "payment_type", "payment_installments",
                                 "payment_value"]]
    return fact_orders, fact_order_items, fact_payments


# ---------------------------------------------------------------------------
# 4. KPIs and preview charts
# ---------------------------------------------------------------------------

def compute_kpis(fact_orders) -> dict:
    delivered = fact_orders[fact_orders["order_status"].isin(["delivered", "shipped"])]
    revenue = delivered["revenue"].sum()
    return {
        "total_revenue":     revenue,
        "orders":            int(delivered["order_id"].nunique()),
        "avg_order_value":   delivered["revenue"].mean(),
        "customers":         int(delivered["customer_id"].nunique()),
        "repeat_rate_pct":   100 * (
            delivered.groupby("customer_id")["order_id"].nunique() >= 2
        ).mean(),
        "avg_review_score":  delivered["review_score"].mean(),
        "late_share_pct":    100 * delivered["is_late"].mean(),
    }


def chart_kpi_summary(k: dict) -> None:
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.axis("off")
    fig.patch.set_facecolor("#eef2f5")

    cards = [
        ("Total revenue",   f"R$ {k['total_revenue']:>10,.0f}"),
        ("Orders",          f"{k['orders']:>10,}"),
        ("Avg order value", f"R$ {k['avg_order_value']:>10,.2f}"),
        ("Customers",       f"{k['customers']:>10,}"),
        ("Repeat rate",     f"{k['repeat_rate_pct']:>9.1f} %"),
        ("Avg review",      f"{k['avg_review_score']:>10.2f} ★"),
    ]
    for i, (label, val) in enumerate(cards):
        x = 0.02 + (i % 3) * 0.33
        y = 0.55 - (i // 3) * 0.45
        ax.add_patch(plt.Rectangle((x, y), 0.30, 0.36,
                                    facecolor="white",
                                    edgecolor="#dfe6ec"))
        ax.text(x + 0.015, y + 0.22, label,
                fontsize=10, color="#3a86ff", weight="bold",
                transform=ax.transAxes)
        ax.text(x + 0.015, y + 0.06, val,
                fontsize=18, color="#073b4c",
                family="monospace", transform=ax.transAxes)
    ax.set_title("Page-1 KPI cards (preview)", fontsize=12, pad=12)
    plt.tight_layout()
    plt.savefig(OUT_FIGS / "kpi_summary.png", dpi=110)
    plt.close(fig)


def chart_retention(fact_orders, dim_customer) -> None:
    delivered = fact_orders[fact_orders["order_status"] == "delivered"].copy()
    delivered["order_month"] = pd.to_datetime(
        delivered["order_purchase_ts"]
    ).dt.to_period("M").astype(str)
    cohort = delivered.merge(
        dim_customer[["customer_id", "cohort_month"]], on="customer_id"
    )
    cohort["months_since"] = (
        (pd.to_datetime(cohort["order_month"]).dt.year
         - pd.to_datetime(cohort["cohort_month"]).dt.year) * 12
        + (pd.to_datetime(cohort["order_month"]).dt.month
           - pd.to_datetime(cohort["cohort_month"]).dt.month)
    )
    sizes = cohort.groupby("cohort_month")["customer_id"].nunique()
    counts = (cohort.groupby(["cohort_month", "months_since"])["customer_id"]
              .nunique().reset_index(name="active"))
    counts["pct"] = 100 * counts["active"] / counts["cohort_month"].map(sizes)
    pivot = counts.pivot(index="cohort_month", columns="months_since",
                         values="pct").iloc[:14, :13]

    fig, ax = plt.subplots(figsize=(11, 5.5))
    im = ax.imshow(pivot.values, cmap="YlOrRd", aspect="auto", vmin=0, vmax=100)
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    ax.set_xlabel("Months since first order")
    ax.set_ylabel("Cohort")
    ax.set_title("Customer cohort retention (% active in month X)")
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            v = pivot.values[i, j]
            if pd.notna(v) and v > 0:
                ax.text(j, i, f"{v:.0f}", ha="center", va="center",
                        fontsize=8,
                        color="black" if v < 50 else "white")
    fig.colorbar(im, ax=ax, label="Retention %")
    plt.tight_layout()
    plt.savefig(OUT_FIGS / "retention_heatmap.png", dpi=110)
    plt.close(fig)


# ---------------------------------------------------------------------------
# 5. Driver
# ---------------------------------------------------------------------------

def main() -> None:
    customers, sellers, products, orders, items, payments, reviews, cat = load_raw()

    print("\nBuilding dimensions...")
    dim_date, dim_customer, dim_product, dim_seller = build_dimensions(
        customers, sellers, products, orders, cat
    )

    print("Building facts...")
    fact_orders, fact_order_items, fact_payments = build_facts(
        orders, items, payments, reviews
    )

    # Persist for Power BI
    print("\nWriting Power BI tables...")
    for name, df in [
        ("dim_date",         dim_date),
        ("dim_customer",     dim_customer),
        ("dim_product",      dim_product),
        ("dim_seller",       dim_seller),
        ("fact_orders",      fact_orders),
        ("fact_order_items", fact_order_items),
        ("fact_payments",    fact_payments),
    ]:
        df.to_csv(OUT_DATA / f"{name}.csv", index=False)
        print(f"  {name+'.csv':28s} {len(df):>7,} rows")

    # KPI report and previews
    k = compute_kpis(fact_orders)
    print("\n=== KPIs ===")
    print(f"  Total revenue   : R$ {k['total_revenue']:>10,.0f}")
    print(f"  Orders          :    {k['orders']:>10,}")
    print(f"  Avg order value : R$ {k['avg_order_value']:>10,.2f}")
    print(f"  Customers       :    {k['customers']:>10,}")
    print(f"  Repeat rate     :    {k['repeat_rate_pct']:>9.1f} %")
    print(f"  Avg review      :    {k['avg_review_score']:>10.2f}")
    print(f"  Late share      :    {k['late_share_pct']:>9.1f} %")

    chart_kpi_summary(k)
    chart_retention(fact_orders, dim_customer)
    print(f"\nPreview charts → {OUT_FIGS.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()

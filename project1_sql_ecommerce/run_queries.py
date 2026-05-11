"""
E-Commerce SQL Analysis — Self-contained runner
================================================

Builds an in-memory SQLite database from the canonical schema.sql and
seed_data.sql files, runs the ten analytical queries, saves each
result as a CSV under ``sample_outputs/`` and produces a chart for the
queries where one is meaningful.

The canonical queries.sql file targets PostgreSQL. SQLite-compatible
versions are defined inline below — the differences are minor
(DATE_TRUNC, EXTRACT, AGE …) and explicitly documented next to each
query.

Run with::

    python run_queries.py

Outputs land in ``sample_outputs/`` (CSV per query + a PNG chart for
queries 1, 2, 3, 4, 7 and 9).
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

ROOT = Path(__file__).parent
OUTPUT_DIR = ROOT / "sample_outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

CHART_STYLE = {
    "figure.dpi": 110,
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
}
plt.rcParams.update(CHART_STYLE)
PALETTE = ["#3a86ff", "#fb5607", "#ffbe0b", "#8338ec", "#06d6a0",
           "#ef476f", "#118ab2", "#073b4c"]


# ---------------------------------------------------------------------------
# SQL helpers
# ---------------------------------------------------------------------------

def postgres_to_sqlite_ddl(sql: str) -> str:
    """Translate the Postgres DDL to something SQLite accepts.

    SQLite is strict about a few keywords that Postgres tolerates. The
    transformations are intentionally narrow so the canonical .sql file
    remains valid Postgres.
    """
    sql = re.sub(r"DROP TABLE IF EXISTS\s+(\w+)\s+CASCADE",
                 r"DROP TABLE IF EXISTS \1", sql, flags=re.IGNORECASE)
    sql = re.sub(r"SERIAL\s+PRIMARY KEY",
                 "INTEGER PRIMARY KEY AUTOINCREMENT", sql, flags=re.IGNORECASE)
    sql = re.sub(r"VARCHAR\(\d+\)", "TEXT", sql, flags=re.IGNORECASE)
    sql = re.sub(r"NUMERIC\(\d+\s*,\s*\d+\)", "REAL", sql, flags=re.IGNORECASE)
    return sql


def build_db() -> sqlite3.Connection:
    """Create an in-memory SQLite DB and load schema + seed data."""
    schema_sql = (ROOT / "schema.sql").read_text(encoding="utf-8")
    seed_sql = (ROOT / "seed_data.sql").read_text(encoding="utf-8")

    conn = sqlite3.connect(":memory:")
    conn.executescript(postgres_to_sqlite_ddl(schema_sql))
    conn.executescript(seed_sql)
    return conn


def run(conn: sqlite3.Connection, sql: str) -> pd.DataFrame:
    """Execute a SELECT and return a DataFrame."""
    return pd.read_sql_query(sql, conn)


def save(df: pd.DataFrame, name: str) -> None:
    df.to_csv(OUTPUT_DIR / f"{name}.csv", index=False)


def fmt_eur(ax: plt.Axes) -> None:
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"€{x:,.0f}")
    )


# ---------------------------------------------------------------------------
# Queries — SQLite versions
# ---------------------------------------------------------------------------

Q01_MONTHLY_REVENUE = """
SELECT
    strftime('%Y-%m', p.payment_date)        AS month,
    COUNT(DISTINCT o.order_id)               AS total_orders,
    ROUND(SUM(oi.quantity * oi.unit_price), 2) AS gross_revenue,
    ROUND(AVG(oi.quantity * oi.unit_price), 2) AS avg_order_value
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
JOIN payments p     ON o.order_id = p.order_id
WHERE o.status = 'completed'
GROUP BY month
ORDER BY month;
"""

Q02_TOP_PRODUCTS = """
SELECT
    p.product_id,
    p.name                                                  AS product_name,
    p.category,
    SUM(oi.quantity)                                        AS units_sold,
    ROUND(SUM(oi.quantity * oi.unit_price), 2)              AS total_revenue,
    ROUND(SUM(oi.quantity * p.cost_price), 2)               AS total_cost,
    ROUND(SUM(oi.quantity * (oi.unit_price - p.cost_price)), 2)
                                                            AS gross_margin,
    ROUND(
        100.0 * SUM(oi.quantity * (oi.unit_price - p.cost_price))
        / NULLIF(SUM(oi.quantity * oi.unit_price), 0),
    1)                                                      AS margin_pct
FROM products p
JOIN order_items oi ON p.product_id = oi.product_id
JOIN orders o       ON oi.order_id  = o.order_id
WHERE o.status = 'completed'
GROUP BY p.product_id, p.name, p.category
ORDER BY gross_margin DESC
LIMIT 10;
"""

Q03_LTV = """
WITH customer_spend AS (
    SELECT
        c.customer_id, c.name, c.city, c.signup_date,
        COUNT(DISTINCT o.order_id)                  AS total_orders,
        ROUND(SUM(oi.quantity * oi.unit_price), 2)  AS lifetime_value,
        MIN(o.order_date)                           AS first_order,
        MAX(o.order_date)                           AS last_order
    FROM customers c
    JOIN orders o       ON c.customer_id = o.customer_id
    JOIN order_items oi ON o.order_id    = oi.order_id
    WHERE o.status = 'completed'
    GROUP BY c.customer_id, c.name, c.city, c.signup_date
)
SELECT
    *,
    RANK() OVER (ORDER BY lifetime_value DESC)  AS ltv_rank,
    ROUND(lifetime_value / total_orders, 2)     AS avg_order_value
FROM customer_spend
ORDER BY ltv_rank;
"""

# Q4 — Cohort retention. SQLite has no AGE(); months_since_signup is
# computed from year and month parts directly.
Q04_COHORT_RETENTION = """
WITH cohorts AS (
    SELECT
        c.customer_id,
        strftime('%Y-%m', c.signup_date) AS cohort_month,
        strftime('%Y-%m', o.order_date)  AS order_month
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.status = 'completed'
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(DISTINCT customer_id) AS cohort_size
    FROM cohorts GROUP BY cohort_month
),
retention AS (
    SELECT
        cohort_month,
        order_month,
        COUNT(DISTINCT customer_id) AS active_customers,
        (CAST(substr(order_month, 1, 4) AS INT)
         - CAST(substr(cohort_month, 1, 4) AS INT)) * 12
        + (CAST(substr(order_month, 6, 2) AS INT)
           - CAST(substr(cohort_month, 6, 2) AS INT)) AS months_since_signup
    FROM cohorts
    GROUP BY cohort_month, order_month
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
"""

Q05_RFM = """
WITH rfm_raw AS (
    SELECT
        c.customer_id, c.name,
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
        NTILE(3) OVER (ORDER BY last_order_date DESC) AS r_score,
        NTILE(3) OVER (ORDER BY frequency       DESC) AS f_score,
        NTILE(3) OVER (ORDER BY monetary        DESC) AS m_score
    FROM rfm_raw
)
SELECT
    customer_id, name, last_order_date, frequency,
    ROUND(monetary, 2)            AS monetary,
    r_score, f_score, m_score,
    (r_score + f_score + m_score) AS rfm_total,
    CASE
        WHEN (r_score + f_score + m_score) >= 8           THEN 'Champions'
        WHEN (r_score + f_score + m_score) >= 6           THEN 'Loyal Customers'
        WHEN r_score = 3 AND (f_score + m_score) <= 3     THEN 'New Customers'
        WHEN r_score <= 2 AND f_score >= 2                THEN 'At Risk'
        ELSE 'Need Attention'
    END                            AS segment
FROM rfm_scores
ORDER BY rfm_total DESC;
"""

# Q6 — Days since last order: julianday() in SQLite gives a real number
# (not an interval), so we cast to integer for readability.
Q06_FIRST_VS_REPEAT = """
WITH ranked_orders AS (
    SELECT
        o.order_id, o.customer_id, c.name, o.order_date,
        ROW_NUMBER() OVER (
            PARTITION BY o.customer_id ORDER BY o.order_date
        ) AS order_rank,
        LAG(o.order_date) OVER (
            PARTITION BY o.customer_id ORDER BY o.order_date
        ) AS previous_order_date
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE o.status = 'completed'
)
SELECT
    order_id, customer_id, name, order_date, order_rank,
    CASE WHEN order_rank = 1 THEN 'First Purchase' ELSE 'Repeat Purchase' END
        AS purchase_type,
    previous_order_date,
    CAST(julianday(order_date) - julianday(previous_order_date) AS INT)
        AS days_since_last_order
FROM ranked_orders
ORDER BY customer_id, order_rank;
"""

Q07_YOY = """
SELECT
    p.category,
    ROUND(SUM(CASE WHEN strftime('%Y', o.order_date) = '2022'
                   THEN oi.quantity * oi.unit_price ELSE 0 END), 2)
                                                            AS revenue_2022,
    ROUND(SUM(CASE WHEN strftime('%Y', o.order_date) = '2023'
                   THEN oi.quantity * oi.unit_price ELSE 0 END), 2)
                                                            AS revenue_2023,
    ROUND(
        100.0 * (
            SUM(CASE WHEN strftime('%Y', o.order_date) = '2023'
                     THEN oi.quantity * oi.unit_price ELSE 0 END)
            - SUM(CASE WHEN strftime('%Y', o.order_date) = '2022'
                       THEN oi.quantity * oi.unit_price ELSE 0 END)
        ) / NULLIF(
            SUM(CASE WHEN strftime('%Y', o.order_date) = '2022'
                     THEN oi.quantity * oi.unit_price ELSE 0 END), 0),
    1)                                                      AS yoy_growth_pct
FROM products p
JOIN order_items oi ON p.product_id = oi.product_id
JOIN orders o       ON oi.order_id  = o.order_id
WHERE o.status = 'completed'
GROUP BY p.category
ORDER BY revenue_2023 DESC;
"""

Q08_DATA_QUALITY = """
SELECT
    o.order_id, o.customer_id, c.name AS customer_name,
    o.order_date, o.status,
    SUM(oi.quantity * oi.unit_price) AS order_total
FROM orders o
LEFT JOIN payments p  ON o.order_id    = p.order_id
JOIN customers c      ON o.customer_id = c.customer_id
JOIN order_items oi   ON o.order_id    = oi.order_id
WHERE p.payment_id IS NULL
  AND o.status NOT IN ('cancelled', 'refunded')
GROUP BY o.order_id, o.customer_id, c.name, o.order_date, o.status
ORDER BY o.order_date;
"""

Q09_RUNNING_TOTAL = """
WITH daily_revenue AS (
    SELECT p.payment_date AS day, SUM(p.amount) AS daily_revenue
    FROM payments p
    JOIN orders o ON p.order_id = o.order_id
    WHERE o.status = 'completed'
    GROUP BY p.payment_date
)
SELECT
    day,
    ROUND(daily_revenue, 2)         AS daily_revenue,
    ROUND(SUM(daily_revenue) OVER (
        ORDER BY day
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ), 2)                            AS running_total,
    ROUND(AVG(daily_revenue) OVER (
        ORDER BY day
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 2)                            AS rolling_7day_avg
FROM daily_revenue
ORDER BY day;
"""

Q10_PLAN_HINT = """
EXPLAIN QUERY PLAN
SELECT
    o.order_id, o.order_date, c.name,
    SUM(oi.quantity * oi.unit_price) AS order_total
FROM orders o
JOIN customers c    ON o.customer_id = c.customer_id
JOIN order_items oi ON o.order_id    = oi.order_id
WHERE o.order_date BETWEEN '2023-01-01' AND '2023-06-30'
  AND o.status = 'completed'
GROUP BY o.order_id, o.order_date, c.name
ORDER BY order_total DESC;
"""


# ---------------------------------------------------------------------------
# Charts — one per query that benefits from one
# ---------------------------------------------------------------------------

def chart_q01(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.bar(df["month"], df["gross_revenue"], color=PALETTE[0])
    ax.set_title("Q1 · Monthly Gross Revenue (completed orders)")
    ax.set_ylabel("Revenue")
    fmt_eur(ax)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "01_monthly_revenue.png")
    plt.close(fig)


def chart_q02(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.barh(df["product_name"][::-1], df["gross_margin"][::-1], color=PALETTE[1])
    ax.set_title("Q2 · Top 10 Products by Gross Margin")
    ax.set_xlabel("Gross margin")
    ax.xaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"€{x:,.0f}")
    )
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "02_top_products_margin.png")
    plt.close(fig)


def chart_q03(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.5))
    top = df.head(10)
    ax.barh(top["name"][::-1], top["lifetime_value"][::-1], color=PALETTE[3])
    ax.set_title("Q3 · Top 10 Customers by Lifetime Value")
    ax.set_xlabel("LTV")
    ax.xaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"€{x:,.0f}")
    )
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "03_top_ltv_customers.png")
    plt.close(fig)


def chart_q04(df: pd.DataFrame) -> None:
    if df.empty:
        return
    pivot = df.pivot_table(
        index="cohort_month",
        columns="months_since_signup",
        values="retention_pct",
        aggfunc="mean",
    )
    fig, ax = plt.subplots(figsize=(10, 5))
    im = ax.imshow(pivot.values, cmap="YlOrRd", aspect="auto")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    ax.set_xlabel("Months since signup")
    ax.set_ylabel("Cohort")
    ax.set_title("Q4 · Cohort Retention (% of cohort active in month X)")
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            v = pivot.values[i, j]
            if pd.notna(v):
                ax.text(j, i, f"{v:.0f}", ha="center", va="center",
                        fontsize=8, color="black" if v < 60 else "white")
    fig.colorbar(im, ax=ax, label="Retention %")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "04_cohort_retention.png")
    plt.close(fig)


def chart_q05(df: pd.DataFrame) -> None:
    counts = df["segment"].value_counts()
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(counts.index, counts.values, color=PALETTE[:len(counts)])
    ax.set_title("Q5 · Customers per RFM Segment")
    ax.set_ylabel("Customers")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "05_rfm_segments.png")
    plt.close(fig)


def chart_q07(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = range(len(df))
    width = 0.4
    ax.bar([i - width/2 for i in x], df["revenue_2022"],
           width=width, label="2022", color=PALETTE[0])
    ax.bar([i + width/2 for i in x], df["revenue_2023"],
           width=width, label="2023", color=PALETTE[1])
    ax.set_xticks(list(x))
    ax.set_xticklabels(df["category"])
    ax.set_title("Q7 · Year-over-Year Revenue by Category")
    ax.set_ylabel("Revenue")
    fmt_eur(ax)
    ax.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "07_yoy_by_category.png")
    plt.close(fig)


def chart_q09(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.bar(df["day"], df["daily_revenue"], color=PALETTE[0],
           alpha=0.55, label="Daily revenue")
    ax2 = ax.twinx()
    ax2.plot(df["day"], df["running_total"], color=PALETTE[3],
             linewidth=2.2, label="Running total")
    ax2.plot(df["day"], df["rolling_7day_avg"], color=PALETTE[1],
             linewidth=2.2, linestyle="--", label="7-day rolling avg")
    ax.set_title("Q9 · Daily Revenue, Running Total and 7-Day Rolling Avg")
    ax.set_ylabel("Daily revenue")
    ax2.set_ylabel("Running total / Rolling avg")
    fmt_eur(ax)
    ax2.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"€{x:,.0f}")
    )
    ax.tick_params(axis="x", rotation=45)
    fig.legend(loc="upper left", bbox_to_anchor=(0.1, 0.95))
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "09_running_total.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

QUERIES = [
    ("01_monthly_revenue",     Q01_MONTHLY_REVENUE,  chart_q01),
    ("02_top_products_margin", Q02_TOP_PRODUCTS,     chart_q02),
    ("03_customer_ltv",        Q03_LTV,              chart_q03),
    ("04_cohort_retention",    Q04_COHORT_RETENTION, chart_q04),
    ("05_rfm_segments",        Q05_RFM,              chart_q05),
    ("06_first_vs_repeat",     Q06_FIRST_VS_REPEAT,  None),
    ("07_yoy_by_category",     Q07_YOY,              chart_q07),
    ("08_data_quality",        Q08_DATA_QUALITY,     None),
    ("09_running_total",       Q09_RUNNING_TOTAL,    chart_q09),
]


def main() -> None:
    conn = build_db()
    print("Database loaded.\n")

    for name, sql, charter in QUERIES:
        df = run(conn, sql)
        save(df, name)
        print(f"=== {name}  ({len(df)} rows) ===")
        print(df.head(8).to_string(index=False))
        print()
        if charter is not None:
            charter(df)

    plan = run(conn, Q10_PLAN_HINT)
    print("=== 10_query_plan ===")
    print(plan.to_string(index=False))
    plan.to_csv(OUTPUT_DIR / "10_query_plan.csv", index=False)

    print(f"\nAll outputs saved under {OUTPUT_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()

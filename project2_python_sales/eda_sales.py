"""
Sales Performance — Exploratory Data Analysis
==============================================

End-to-end EDA on a retail sales dataset. The dataset is synthetic
(generation routine in section 2) and is built so the analysis has
real seasonality, channel mix and category effects to discover. The
goal is to show the *workflow* a junior analyst would follow on real
business data, not to "discover" anything that wasn't put in.

Run with::

    pip install -r requirements.txt
    python eda_sales.py

All figures are saved under ``outputs/`` (PNG, 110 dpi).

Author : Roger Amorín Suñé
Stack  : Python · Pandas · NumPy · Matplotlib · Seaborn
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns

warnings.filterwarnings("ignore")
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams.update({"figure.dpi": 110, "font.size": 11})

ROOT = Path(__file__).parent
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# 1. DATA — SYNTHETIC GENERATION
# ---------------------------------------------------------------------------
#
# The dataset is built with explicit, *documented* effects:
#   * Q4 lift of +20% in Oct–Nov–Dec
#   * Online channel weighted to ~65 %
#   * Electronics ~40 % of the category mix
#
# These effects are then *measured* in the EDA. The point is to walk
# through how an analyst would quantify and communicate them — not to
# claim a discovery that was already known by construction.
# ---------------------------------------------------------------------------

def build_dataset(n: int = 1_000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    categories = ["Electronics", "Furniture", "Books", "Stationery"]
    cat_weights = [0.40, 0.25, 0.20, 0.15]
    regions = ["Barcelona", "Madrid", "Valencia", "Sevilla", "Bilbao"]
    channels = ["Online", "In-store"]

    dates = pd.date_range("2022-01-01", "2023-12-31", periods=n)
    category = rng.choice(categories, n, p=cat_weights)
    region = rng.choice(regions, n)
    channel = rng.choice(channels, n, p=[0.65, 0.35])

    price_map = {
        "Electronics": (50, 1200),
        "Furniture":   (80,  700),
        "Books":       (10,   35),
        "Stationery":  ( 3,   25),
    }
    unit_price = np.array([rng.uniform(*price_map[c]) for c in category])
    quantity = rng.choice([1, 2, 3], n, p=[0.70, 0.20, 0.10])
    revenue = unit_price * quantity

    # Documented Q4 lift (+20 %).
    month = pd.DatetimeIndex(dates).month
    revenue = revenue * np.where(month.isin([10, 11, 12]), 1.20, 1.0)

    df = pd.DataFrame(
        {
            "date":       dates,
            "category":   category,
            "region":     region,
            "channel":    channel,
            "unit_price": unit_price.round(2),
            "quantity":   quantity,
            "revenue":    revenue.round(2),
        }
    )
    df["year"]        = df["date"].dt.year
    df["month"]       = df["date"].dt.month
    df["quarter"]     = df["date"].dt.quarter
    df["month_label"] = df["date"].dt.to_period("M").astype(str)
    return df


# ---------------------------------------------------------------------------
# 2. PLOTTING HELPERS
# ---------------------------------------------------------------------------

def fmt_eur(ax: plt.Axes) -> None:
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"€{x:,.0f}")
    )


def save(fig: plt.Figure, name: str) -> None:
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=110)
    plt.close(fig)


# ---------------------------------------------------------------------------
# 3. ANALYSES — each function returns the figure it produced
# ---------------------------------------------------------------------------

def plot_monthly_revenue(df: pd.DataFrame) -> None:
    monthly = df.groupby("month_label")["revenue"].sum().reset_index()
    monthly["rolling_avg"] = monthly["revenue"].rolling(3, min_periods=1).mean()

    fig, ax = plt.subplots(figsize=(13, 4))
    ax.bar(monthly["month_label"], monthly["revenue"],
           color=sns.color_palette("muted")[0], alpha=0.75,
           label="Monthly revenue")
    ax.plot(monthly["month_label"], monthly["rolling_avg"],
            color="tomato", linewidth=2.5, label="3-month rolling avg")
    ax.set_title("Monthly Revenue with 3-Month Rolling Average")
    ax.set_ylabel("Revenue")
    fmt_eur(ax)
    plt.xticks(rotation=45, ha="right")
    ax.legend()
    save(fig, "01_monthly_revenue.png")


def plot_revenue_by_category(df: pd.DataFrame) -> None:
    cat_rev = df.groupby("category")["revenue"].sum().sort_values(ascending=False)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    palette = sns.color_palette("muted", len(cat_rev))

    bars = axes[0].bar(cat_rev.index, cat_rev.values, color=palette)
    axes[0].set_title("Revenue by Category")
    axes[0].set_ylabel("Revenue")
    fmt_eur(axes[0])
    for bar, val in zip(bars, cat_rev.values):
        axes[0].text(bar.get_x() + bar.get_width() / 2,
                     bar.get_height() + cat_rev.max() * 0.01,
                     f"€{val:,.0f}", ha="center", va="bottom", fontsize=9)

    axes[1].pie(cat_rev.values, labels=cat_rev.index,
                autopct="%1.1f%%", startangle=90, colors=palette)
    axes[1].set_title("Revenue Share by Category")
    save(fig, "02_revenue_by_category.png")


def plot_seasonality_heatmap(df: pd.DataFrame) -> None:
    pivot = df.pivot_table(values="revenue", index="month",
                           columns="year", aggfunc="sum")
    pivot.index = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    fig, ax = plt.subplots(figsize=(7, 6))
    sns.heatmap(pivot, annot=True, fmt=",.0f", cmap="YlOrRd",
                linewidths=0.5, ax=ax, annot_kws={"size": 9})
    ax.set_title("Revenue Heatmap: Month × Year")
    ax.set_xlabel("Year")
    ax.set_ylabel("Month")
    save(fig, "03_seasonality_heatmap.png")


def plot_channel_comparison(df: pd.DataFrame) -> None:
    monthly_channel = (df.groupby(["month_label", "channel"])["revenue"]
                       .sum().unstack().reset_index())

    fig, ax = plt.subplots(figsize=(13, 4))
    x = range(len(monthly_channel))
    w = 0.4
    palette = sns.color_palette("muted")
    ax.bar([i - w / 2 for i in x], monthly_channel["Online"],
           width=w, label="Online", color=palette[0], alpha=0.85)
    ax.bar([i + w / 2 for i in x], monthly_channel["In-store"],
           width=w, label="In-store", color=palette[1], alpha=0.85)
    ax.set_xticks(list(x))
    ax.set_xticklabels(monthly_channel["month_label"], rotation=45, ha="right")
    ax.set_title("Monthly Revenue: Online vs In-store")
    ax.set_ylabel("Revenue")
    fmt_eur(ax)
    ax.legend()
    save(fig, "04_channel_comparison.png")


def plot_revenue_distribution(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    order = df.groupby("category")["revenue"].median()\
              .sort_values(ascending=False).index
    sns.boxplot(data=df, x="category", y="revenue",
                order=order, palette="muted", ax=ax)
    ax.set_title("Revenue Distribution per Transaction by Category")
    ax.set_xlabel("")
    ax.set_ylabel("Revenue per transaction")
    fmt_eur(ax)
    save(fig, "05_revenue_distribution.png")


def plot_revenue_by_region(df: pd.DataFrame) -> None:
    pivot_region = (df.groupby(["region", "category"])["revenue"]
                    .sum().unstack().fillna(0))
    pivot_region = pivot_region.loc[
        pivot_region.sum(axis=1).sort_values(ascending=False).index
    ]

    fig, ax = plt.subplots(figsize=(10, 5))
    pivot_region.plot(kind="bar", stacked=True, ax=ax,
                      color=sns.color_palette("muted", pivot_region.shape[1]),
                      edgecolor="white", linewidth=0.4)
    ax.set_title("Revenue by Region and Category")
    ax.set_xlabel("")
    ax.set_ylabel("Revenue")
    fmt_eur(ax)
    ax.legend(title="Category", bbox_to_anchor=(1.01, 1), loc="upper left")
    plt.xticks(rotation=30, ha="right")
    save(fig, "06_revenue_by_region.png")


# ---------------------------------------------------------------------------
# 4. SUMMARY — values that go straight into the README / a Power BI card
# ---------------------------------------------------------------------------

def summarise(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Revenue (€)":    df.groupby("category")["revenue"].sum().round(0),
            "Transactions":   df.groupby("category")["revenue"].count(),
            "Avg Ticket (€)": df.groupby("category")["revenue"].mean().round(2),
            "Share (%)":     (df.groupby("category")["revenue"].sum()
                              / df["revenue"].sum() * 100).round(1),
        }
    ).sort_values("Revenue (€)", ascending=False)


def kpis(df: pd.DataFrame) -> dict[str, float]:
    total = df["revenue"].sum()
    q4 = df.loc[df["month"].isin([10, 11, 12]), "revenue"].sum()
    online = df.loc[df["channel"] == "Online", "revenue"].sum()
    return {
        "total_revenue":       total,
        "transactions":        len(df),
        "avg_ticket":          df["revenue"].mean(),
        "q4_share_pct":        100 * q4 / total,
        "online_share_pct":    100 * online / total,
        "electronics_share":   100 *
            df.loc[df["category"] == "Electronics", "revenue"].sum() / total,
    }


# ---------------------------------------------------------------------------
# 5. DRIVER
# ---------------------------------------------------------------------------

def main() -> None:
    df = build_dataset()
    print(f"Dataset: {df.shape[0]:,} rows × {df.shape[1]} columns")
    print(f"Date range: {df['date'].min().date()} → {df['date'].max().date()}\n")

    print("=== Category summary ===")
    print(summarise(df).to_string())

    k = kpis(df)
    print("\n=== Key KPIs ===")
    print(f"  Total revenue       : €{k['total_revenue']:>10,.0f}")
    print(f"  Transactions        :  {k['transactions']:>10,}")
    print(f"  Avg ticket          : €{k['avg_ticket']:>10,.2f}")
    print(f"  Q4 share            : {k['q4_share_pct']:>10.1f} %")
    print(f"  Online share        : {k['online_share_pct']:>10.1f} %")
    print(f"  Electronics share   : {k['electronics_share']:>10.1f} %")

    plot_monthly_revenue(df)
    plot_revenue_by_category(df)
    plot_seasonality_heatmap(df)
    plot_channel_comparison(df)
    plot_revenue_distribution(df)
    plot_revenue_by_region(df)
    print(f"\n6 charts saved under {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()

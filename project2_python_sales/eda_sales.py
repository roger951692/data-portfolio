# ============================================================
# Sales Performance — Exploratory Data Analysis
# Author: Roger | Stack: Python, Pandas, NumPy, Matplotlib, Seaborn
# ============================================================
#
# This script can be run directly or converted to a Jupyter Notebook:
#   pip install jupytext
#   jupytext --to notebook eda_sales.py
# ============================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ── Style ────────────────────────────────────────────────────
sns.set_theme(style='whitegrid', palette='muted')
plt.rcParams.update({'figure.dpi': 120, 'font.size': 11})

# ============================================================
# 1. GENERATE SYNTHETIC DATASET
# ============================================================
# Reproducible retail sales data: 1,000 transactions, 2022-2023

np.random.seed(42)
N = 1000

categories   = ['Electronics', 'Furniture', 'Books', 'Stationery']
cat_weights  = [0.40, 0.25, 0.20, 0.15]
regions      = ['Barcelona', 'Madrid', 'Valencia', 'Sevilla', 'Bilbao']
channels     = ['Online', 'In-store']

dates = pd.date_range('2022-01-01', '2023-12-31', periods=N)
dates = dates + pd.to_timedelta(np.random.randint(0, 24, N), unit='h')

category     = np.random.choice(categories, N, p=cat_weights)
region       = np.random.choice(regions, N)
channel      = np.random.choice(channels, N, p=[0.65, 0.35])

# Price depends on category
price_map = {'Electronics': (50, 1200), 'Furniture': (80, 700),
             'Books': (10, 35),          'Stationery': (3, 25)}
unit_price = np.array([
    np.random.uniform(*price_map[c]) for c in category
])
quantity   = np.random.choice([1, 2, 3], N, p=[0.70, 0.20, 0.10])
revenue    = unit_price * quantity

# Inject slight seasonality: Q4 boost (+20%)
month = pd.DatetimeIndex(dates).month
seasonal_factor = np.where(month.isin([10, 11, 12]), 1.20, 1.0)
revenue = revenue * seasonal_factor

df = pd.DataFrame({
    'date':       dates,
    'category':   category,
    'region':     region,
    'channel':    channel,
    'unit_price': unit_price.round(2),
    'quantity':   quantity,
    'revenue':    revenue.round(2)
})
df['year']  = df['date'].dt.year
df['month'] = df['date'].dt.month
df['quarter'] = df['date'].dt.quarter
df['month_label'] = df['date'].dt.to_period('M')

print("=" * 55)
print("DATASET OVERVIEW")
print("=" * 55)
print(df.dtypes)
print(f"\nShape: {df.shape}")
print(f"\nDate range: {df['date'].min().date()} → {df['date'].max().date()}")
print(f"\nMissing values:\n{df.isnull().sum()}")


# ============================================================
# 2. SUMMARY STATISTICS
# ============================================================

print("\n" + "=" * 55)
print("SUMMARY STATISTICS")
print("=" * 55)

total_revenue = df['revenue'].sum()
total_orders  = len(df)
avg_order     = df['revenue'].mean()

print(f"Total Revenue:     €{total_revenue:,.0f}")
print(f"Total Transactions:{total_orders:,}")
print(f"Avg Order Value:   €{avg_order:.2f}")
print(f"\nRevenue by Category:\n{df.groupby('category')['revenue'].sum().sort_values(ascending=False).apply(lambda x: f'€{x:,.0f}')}")
print(f"\nRevenue by Region:\n{df.groupby('region')['revenue'].sum().sort_values(ascending=False).apply(lambda x: f'€{x:,.0f}')}")
print(f"\nRevenue by Channel:\n{df.groupby('channel')['revenue'].sum().sort_values(ascending=False).apply(lambda x: f'€{x:,.0f}')}")


# ============================================================
# 3. MONTHLY REVENUE TREND
# ============================================================

monthly = (df.groupby('month_label')['revenue']
             .sum()
             .reset_index())
monthly['month_label'] = monthly['month_label'].astype(str)

fig, ax = plt.subplots(figsize=(12, 4))
ax.bar(monthly['month_label'], monthly['revenue'],
       color=sns.color_palette('muted')[0], alpha=0.8)

# Rolling average
rolling = monthly['revenue'].rolling(3, min_periods=1).mean()
ax.plot(monthly['month_label'], rolling, color='tomato',
        linewidth=2, label='3-month rolling avg')

ax.set_title('Monthly Revenue with 3-Month Rolling Average', fontsize=13, pad=12)
ax.set_xlabel('')
ax.set_ylabel('Revenue (€)')
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'€{x:,.0f}'))
plt.xticks(rotation=45, ha='right')
ax.legend()
plt.tight_layout()
plt.savefig('01_monthly_revenue.png', bbox_inches='tight')
plt.show()
print("✔ Saved: 01_monthly_revenue.png")


# ============================================================
# 4. REVENUE BY CATEGORY — BAR + PIE
# ============================================================

cat_rev = df.groupby('category')['revenue'].sum().sort_values(ascending=False)

fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# Bar
bars = axes[0].bar(cat_rev.index, cat_rev.values,
                   color=sns.color_palette('muted', len(cat_rev)))
axes[0].set_title('Revenue by Category', fontsize=13)
axes[0].set_ylabel('Revenue (€)')
axes[0].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'€{x:,.0f}'))
for bar, val in zip(bars, cat_rev.values):
    axes[0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 500,
                 f'€{val:,.0f}', ha='center', va='bottom', fontsize=9)

# Pie
axes[1].pie(cat_rev.values, labels=cat_rev.index,
            autopct='%1.1f%%', startangle=90,
            colors=sns.color_palette('muted', len(cat_rev)))
axes[1].set_title('Revenue Share by Category', fontsize=13)

plt.tight_layout()
plt.savefig('02_revenue_by_category.png', bbox_inches='tight')
plt.show()
print("✔ Saved: 02_revenue_by_category.png")


# ============================================================
# 5. SEASONALITY ANALYSIS — HEATMAP (Month x Year)
# ============================================================

pivot = df.pivot_table(values='revenue', index='month',
                       columns='year', aggfunc='sum')
month_names = ['Jan','Feb','Mar','Apr','May','Jun',
               'Jul','Aug','Sep','Oct','Nov','Dec']
pivot.index = month_names

fig, ax = plt.subplots(figsize=(8, 6))
sns.heatmap(pivot, annot=True, fmt=',.0f', cmap='YlOrRd',
            linewidths=0.5, ax=ax,
            annot_kws={'size': 9})
ax.set_title('Revenue Heatmap: Month × Year', fontsize=13, pad=12)
ax.set_xlabel('Year')
ax.set_ylabel('Month')
plt.tight_layout()
plt.savefig('03_seasonality_heatmap.png', bbox_inches='tight')
plt.show()
print("✔ Saved: 03_seasonality_heatmap.png")


# ============================================================
# 6. CHANNEL COMPARISON — ONLINE vs IN-STORE
# ============================================================

channel_monthly = (df.groupby(['month_label', 'channel'])['revenue']
                     .sum()
                     .unstack()
                     .reset_index())
channel_monthly['month_label'] = channel_monthly['month_label'].astype(str)

fig, ax = plt.subplots(figsize=(12, 4))
x = range(len(channel_monthly))
width = 0.4

ax.bar([i - width/2 for i in x], channel_monthly['Online'],
       width=width, label='Online', color=sns.color_palette('muted')[0], alpha=0.85)
ax.bar([i + width/2 for i in x], channel_monthly['In-store'],
       width=width, label='In-store', color=sns.color_palette('muted')[1], alpha=0.85)

ax.set_xticks(list(x))
ax.set_xticklabels(channel_monthly['month_label'], rotation=45, ha='right')
ax.set_title('Monthly Revenue: Online vs In-store', fontsize=13)
ax.set_ylabel('Revenue (€)')
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'€{x:,.0f}'))
ax.legend()
plt.tight_layout()
plt.savefig('04_channel_comparison.png', bbox_inches='tight')
plt.show()
print("✔ Saved: 04_channel_comparison.png")


# ============================================================
# 7. REVENUE DISTRIBUTION — BOXPLOT BY CATEGORY
# ============================================================

fig, ax = plt.subplots(figsize=(10, 5))
order = df.groupby('category')['revenue'].median().sort_values(ascending=False).index
sns.boxplot(data=df, x='category', y='revenue', order=order,
            palette='muted', ax=ax)
ax.set_title('Revenue Distribution per Transaction by Category', fontsize=13)
ax.set_xlabel('')
ax.set_ylabel('Revenue per transaction (€)')
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'€{x:,.0f}'))
plt.tight_layout()
plt.savefig('05_revenue_distribution.png', bbox_inches='tight')
plt.show()
print("✔ Saved: 05_revenue_distribution.png")


# ============================================================
# 8. TOP REGIONS
# ============================================================

region_rev = (df.groupby(['region', 'category'])['revenue']
                .sum()
                .reset_index())

fig, ax = plt.subplots(figsize=(10, 5))
pivot_region = region_rev.pivot(index='region', columns='category', values='revenue').fillna(0)
pivot_region.loc['TOTAL'] = pivot_region.sum()
pivot_region = pivot_region.drop('TOTAL').sort_values(
    pivot_region.columns.tolist(), ascending=False
)
pivot_region.plot(kind='bar', stacked=True, ax=ax,
                  color=sns.color_palette('muted', len(pivot_region.columns)),
                  edgecolor='white', linewidth=0.5)
ax.set_title('Revenue by Region and Category', fontsize=13)
ax.set_xlabel('')
ax.set_ylabel('Revenue (€)')
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'€{x:,.0f}'))
ax.legend(title='Category', bbox_to_anchor=(1.01, 1), loc='upper left')
plt.xticks(rotation=30, ha='right')
plt.tight_layout()
plt.savefig('06_revenue_by_region.png', bbox_inches='tight')
plt.show()
print("✔ Saved: 06_revenue_by_region.png")


# ============================================================
# 9. KEY FINDINGS SUMMARY
# ============================================================

print("\n" + "=" * 55)
print("KEY FINDINGS")
print("=" * 55)

top_cat     = cat_rev.idxmax()
top_cat_pct = cat_rev.max() / cat_rev.sum() * 100
q4_rev      = df[df['quarter'] == 4]['revenue'].sum()
q4_pct      = q4_rev / total_revenue * 100
online_pct  = df[df['channel'] == 'Online']['revenue'].sum() / total_revenue * 100

print(f"1. Top category: {top_cat} ({top_cat_pct:.1f}% of revenue)")
print(f"2. Q4 seasonality: {q4_pct:.1f}% of annual revenue concentrated in Oct-Dec")
print(f"3. Channel split: Online {online_pct:.1f}% | In-store {100-online_pct:.1f}%")
print(f"4. Avg transaction value: €{avg_order:.2f}")
print(f"5. Top region by revenue: {df.groupby('region')['revenue'].sum().idxmax()}")
print("\nAll charts saved as PNG files.")

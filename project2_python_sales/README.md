# Sales Performance — Exploratory Data Analysis

End-to-end EDA on a retail sales dataset covering 1,000 transactions across 2022–2023. Identifies revenue trends, seasonal patterns, channel performance and top-performing segments.

## Objectives

- Understand overall revenue dynamics (monthly trends, YoY)
- Identify seasonal peaks and their business implications
- Compare Online vs In-store channel performance
- Analyse revenue distribution across product categories and regions

## Key Findings

1. **Electronics** is the dominant category, generating ~45% of total revenue
2. **Q4 seasonality** is significant — Oct–Dec concentrates ~28% of annual revenue
3. **Online channel** accounts for ~65% of revenue, growing throughout 2023
4. **Barcelona and Madrid** are the top two regions by volume
5. Revenue per transaction varies widely by category (Books: low ticket, high volume; Electronics: high ticket, lower frequency)

## Structure

```
project2_python_sales/
├── eda_sales.py                  # Main analysis script
├── requirements.txt
└── outputs/
    ├── 01_monthly_revenue.png
    ├── 02_revenue_by_category.png
    ├── 03_seasonality_heatmap.png
    ├── 04_channel_comparison.png
    ├── 05_revenue_distribution.png
    └── 06_revenue_by_region.png
```

## How to run

```bash
pip install -r requirements.txt
python eda_sales.py
```

Or convert to Jupyter Notebook:

```bash
pip install jupytext
jupytext --to notebook eda_sales.py
jupyter notebook eda_sales.ipynb
```

## Stack

- **Python 3.10+**
- **Pandas** — data manipulation
- **NumPy** — numerical operations
- **Matplotlib** — base charting
- **Seaborn** — statistical visualisation

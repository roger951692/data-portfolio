# Project 2 · Sales Performance EDA

End-to-end exploratory analysis of a retail sales dataset (1,000 transactions, 2022–2023, four categories, five regions, two channels). The analysis quantifies seasonality, channel mix, category contribution and per-transaction distribution — the kind of dashboard a junior analyst would build during their first sprint.

## Note on the dataset

The dataset is **synthetic**, generated in Python with documented effects: a +20% Q4 lift, ~65% Online weight and an Electronics-skewed category mix. The point of the analysis is to show **how** an analyst would surface and quantify those effects, not to claim a discovery. Every chart, table and KPI in this notebook would work the same way against real retail data.

A real-world equivalent of this analysis on the Brazilian E-Commerce dataset (~100 K rows, public) is the focus of [Project 3](../project3_ecommerce_dashboard/).

## What's inside

| File | Purpose |
|---|---|
| `eda_sales.ipynb` | The analysis as a Jupyter notebook (renders well on GitHub) |
| `eda_sales.py` | The same analysis as a runnable script (saves all PNGs to `outputs/`) |
| `requirements.txt` | Pandas, NumPy, Matplotlib, Seaborn |
| `outputs/` | Pre-generated charts (PNG, 110 dpi) |

## How to run

```bash
pip install -r requirements.txt
python eda_sales.py
```

Or open `eda_sales.ipynb` in Jupyter Lab / Colab.

## KPIs at a glance

| KPI | Value |
|---|---|
| Total revenue | ~€513 K |
| Transactions | 1,000 |
| Average ticket | €513 |
| Online channel share | 64% |
| Q4 (Oct–Dec) share | 28% |
| Electronics share of revenue | 71% |

## Insight → Recommendation

| # | Insight | Recommended action |
|---|---|---|
| 1 | Electronics generate 71% of revenue with the highest avg ticket (~€903) | Prioritise stock depth and promotions in this category; protect margin during sales |
| 2 | Q4 concentrates 28% of annual revenue (Oct–Dec) | Plan inventory and acquisition spend before October; freeze low-impact projects in Q4 |
| 3 | Online channel is 64% of revenue | Continue weighting digital acquisition and UX improvements; track channel CAC separately |
| 4 | Electronics and Furniture show wide per-transaction spread (€50–€1,200 and €80–€700) | Test bundling and upsells; A/B "frequently bought together" placements |
| 5 | Barcelona and Madrid lead by region | Ringfence growth experiments to these markets first, then expand once a playbook is proven |

## Method

The notebook follows a clean linear flow: build dataset → quality check → summary stats → trend chart → category breakdown → seasonality heatmap → channel comparison → distribution view → regional breakdown → insight table. Every chart is independent and saved as PNG so the README and any deck can pull them in directly.

## Stack

- **Python 3.10+**
- **Pandas / NumPy** for data manipulation
- **Matplotlib / Seaborn** for charts (consistent muted palette, € axis formatter)

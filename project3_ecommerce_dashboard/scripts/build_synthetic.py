"""
Generate Olist-shaped synthetic CSVs for offline development.

Produces 5 K customers, 8 K orders, ~12 K order items, 14 K payments,
6 K reviews, 1 K products, 600 sellers — small enough to run quickly,
big enough to populate every chart in the dashboard.

The schema is identical to the real Olist dataset so all SQL queries
and notebooks work unchanged when the real CSVs are dropped into
``data/raw/``.

Run with::

    python scripts/build_synthetic.py
"""

from __future__ import annotations

import csv
import datetime as dt
import random
import string
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

rng = np.random.default_rng(42)
random.seed(42)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def hex_id(prefix: str = "", length: int = 32) -> str:
    return prefix + "".join(random.choices(string.hexdigits.lower(), k=length))


BR_STATES = ["SP", "RJ", "MG", "RS", "PR", "SC", "BA", "DF", "GO", "ES",
             "PE", "CE", "PA", "MA", "MT", "PB", "MS", "RN", "AM", "AL"]
STATE_WEIGHTS = np.array([41, 13, 11,  6,  6,  5,  4,  3,  3,  2,
                           2,  2,  2,  1,  1,  1,  1,  1,  1,  1], dtype=float)
STATE_WEIGHTS = STATE_WEIGHTS / STATE_WEIGHTS.sum()

CITIES_BY_STATE = {
    "SP": ["sao paulo", "campinas", "guarulhos", "santo andre", "santos"],
    "RJ": ["rio de janeiro", "niteroi", "nova iguacu"],
    "MG": ["belo horizonte", "uberlandia", "contagem"],
    "RS": ["porto alegre", "caxias do sul"],
    "PR": ["curitiba", "londrina"],
    "SC": ["florianopolis", "joinville"],
    "BA": ["salvador", "feira de santana"],
    "DF": ["brasilia"],
    "GO": ["goiania"],
    "ES": ["vitoria"],
    "PE": ["recife"],
    "CE": ["fortaleza"],
}
DEFAULT_CITY = "interior"

CATEGORIES_PT = [
    "cama_mesa_banho", "beleza_saude", "esporte_lazer", "informatica_acessorios",
    "moveis_decoracao", "utilidades_domesticas", "relogios_presentes",
    "telefonia", "automotivo", "brinquedos", "ferramentas_jardim",
    "perfumaria", "papelaria", "bebes", "eletrodomesticos",
]
CATEGORY_TRANSLATION = {
    "cama_mesa_banho":          "bed_bath_table",
    "beleza_saude":             "health_beauty",
    "esporte_lazer":            "sports_leisure",
    "informatica_acessorios":   "computers_accessories",
    "moveis_decoracao":         "furniture_decor",
    "utilidades_domesticas":    "housewares",
    "relogios_presentes":       "watches_gifts",
    "telefonia":                "telephony",
    "automotivo":               "auto",
    "brinquedos":               "toys",
    "ferramentas_jardim":       "garden_tools",
    "perfumaria":               "perfumery",
    "papelaria":                "stationery",
    "bebes":                    "baby",
    "eletrodomesticos":         "appliances",
}
CATEGORY_PRICE = {
    "cama_mesa_banho":         (40, 250),
    "beleza_saude":            (15, 200),
    "esporte_lazer":           (30, 800),
    "informatica_acessorios":  (40, 1200),
    "moveis_decoracao":        (60, 600),
    "utilidades_domesticas":   (25, 350),
    "relogios_presentes":      (90, 800),
    "telefonia":              (100, 1500),
    "automotivo":              (35, 700),
    "brinquedos":              (20, 400),
    "ferramentas_jardim":      (40, 500),
    "perfumaria":              (30, 250),
    "papelaria":               (10, 120),
    "bebes":                   (25, 350),
    "eletrodomesticos":       (150, 2000),
}
PAYMENT_TYPES = ["credit_card", "boleto", "voucher", "debit_card"]
PAYMENT_WEIGHTS = [0.74, 0.19, 0.05, 0.02]


def random_state() -> str:
    return rng.choice(BR_STATES, p=STATE_WEIGHTS)


def random_city(state: str) -> str:
    cities = CITIES_BY_STATE.get(state, [DEFAULT_CITY])
    return random.choice(cities)


def fmt_ts(timestamp: dt.datetime | None) -> str:
    return "" if timestamp is None else timestamp.strftime("%Y-%m-%d %H:%M:%S")


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  {path.name:42s} {len(rows):>7,} rows")


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

def gen_customers(n: int) -> list[dict]:
    out = []
    for _ in range(n):
        state = random_state()
        out.append({
            "customer_id":              hex_id(),
            "customer_unique_id":       hex_id(),
            "customer_zip_code_prefix": f"{rng.integers(1000, 99999):05d}",
            "customer_city":            random_city(state),
            "customer_state":           state,
        })
    return out


def gen_sellers(n: int) -> list[dict]:
    out = []
    for _ in range(n):
        state = random_state()
        out.append({
            "seller_id":              hex_id(),
            "seller_zip_code_prefix": f"{rng.integers(1000, 99999):05d}",
            "seller_city":            random_city(state),
            "seller_state":           state,
        })
    return out


def gen_products(n: int) -> list[dict]:
    out = []
    for _ in range(n):
        cat = random.choice(CATEGORIES_PT)
        out.append({
            "product_id":                 hex_id(),
            "product_category_name":      cat,
            "product_name_lenght":        int(rng.integers(20, 70)),
            "product_description_lenght": int(rng.integers(100, 4000)),
            "product_photos_qty":         int(rng.integers(1, 8)),
            "product_weight_g":           int(rng.integers(100, 5000)),
            "product_length_cm":          int(rng.integers(10, 80)),
            "product_height_cm":          int(rng.integers(5, 60)),
            "product_width_cm":           int(rng.integers(5, 60)),
        })
    return out


def gen_orders_and_items(customers, products, sellers, n_orders):
    """Generate orders, order items, payments, reviews together."""
    orders, items, payments, reviews = [], [], [], []
    start_date = dt.datetime(2017, 1, 1)
    end_date   = dt.datetime(2018, 9, 1)
    span       = (end_date - start_date).total_seconds()

    for _ in range(n_orders):
        order_id = hex_id()
        cust = random.choice(customers)
        purchase = start_date + dt.timedelta(seconds=int(rng.uniform(0, span)))
        approved = purchase + dt.timedelta(hours=int(rng.integers(1, 36)))
        carrier  = approved + dt.timedelta(days=int(rng.integers(1, 5)))

        # Late-delivery probability: 8 % overall, higher in MA/PA/AM (north).
        north = cust["customer_state"] in ("MA", "PA", "AM", "RR", "AC", "AP")
        is_late = rng.random() < (0.18 if north else 0.07)
        estimated = approved + dt.timedelta(days=int(rng.integers(8, 18)))
        if is_late:
            delivered = estimated + dt.timedelta(days=int(rng.integers(2, 12)))
        else:
            delivered = estimated - dt.timedelta(days=int(rng.integers(0, 8)))

        # Status. ~96 % delivered.
        status_roll = rng.random()
        if status_roll < 0.96:
            status = "delivered"
        elif status_roll < 0.985:
            status = "shipped"
            delivered = None
        else:
            status = random.choice(["canceled", "unavailable"])
            delivered = None

        orders.append({
            "order_id":                       order_id,
            "customer_id":                    cust["customer_id"],
            "order_status":                   status,
            "order_purchase_timestamp":       fmt_ts(purchase),
            "order_approved_at":              fmt_ts(approved),
            "order_delivered_carrier_date":   fmt_ts(carrier),
            "order_delivered_customer_date":  fmt_ts(delivered),
            "order_estimated_delivery_date":  fmt_ts(estimated),
        })

        # Order items (1..4)
        n_items = int(rng.choice([1, 2, 3, 4], p=[0.65, 0.22, 0.09, 0.04]))
        order_revenue = 0.0
        for j in range(1, n_items + 1):
            prod = random.choice(products)
            seller = random.choice(sellers)
            cat = prod["product_category_name"]
            low, high = CATEGORY_PRICE[cat]
            price = round(rng.uniform(low, high), 2)
            freight = round(rng.uniform(5, 35), 2)
            order_revenue += price + freight
            items.append({
                "order_id":            order_id,
                "order_item_id":       j,
                "product_id":          prod["product_id"],
                "seller_id":           seller["seller_id"],
                "shipping_limit_date": fmt_ts(carrier),
                "price":               price,
                "freight_value":       freight,
            })

        # Payments — usually 1 row, occasionally split.
        n_pays = int(rng.choice([1, 1, 1, 2, 3], p=[0.78, 0.10, 0.05, 0.05, 0.02]))
        remaining = order_revenue
        for k in range(1, n_pays + 1):
            pay_type = rng.choice(PAYMENT_TYPES, p=PAYMENT_WEIGHTS)
            installments = (
                int(rng.choice([1, 2, 3, 4, 6, 8, 10],
                               p=[0.55, 0.10, 0.10, 0.10, 0.07, 0.05, 0.03]))
                if pay_type == "credit_card" else 1
            )
            amount = round(remaining if k == n_pays
                           else remaining / (n_pays - k + 1), 2)
            remaining -= amount
            payments.append({
                "order_id":             order_id,
                "payment_sequential":   k,
                "payment_type":         pay_type,
                "payment_installments": installments,
                "payment_value":        amount,
            })

        # Review (only on delivered/shipped orders).
        if status in ("delivered", "shipped"):
            base_score = 4.4
            if is_late:
                base_score -= 1.6
            score = int(np.clip(round(rng.normal(base_score, 0.9)), 1, 5))
            reviews.append({
                "review_id":               hex_id(),
                "order_id":                order_id,
                "review_score":            score,
                "review_comment_title":    "",
                "review_comment_message":  "",
                "review_creation_date":    fmt_ts(
                    (delivered or estimated) + dt.timedelta(days=2)
                ),
                "review_answer_timestamp": fmt_ts(
                    (delivered or estimated) + dt.timedelta(days=4)
                ),
            })

    return orders, items, payments, reviews


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(n_customers: int = 5_000, n_orders: int = 8_000,
         n_products: int = 1_000, n_sellers: int = 600) -> None:
    print(f"Generating synthetic Olist-shaped dataset → {RAW}/")
    customers = gen_customers(n_customers)
    sellers   = gen_sellers(n_sellers)
    products  = gen_products(n_products)
    orders, items, payments, reviews = gen_orders_and_items(
        customers, products, sellers, n_orders
    )

    write_csv(RAW / "olist_customers_dataset.csv",
              ["customer_id", "customer_unique_id", "customer_zip_code_prefix",
               "customer_city", "customer_state"],
              [[c[k] for k in ["customer_id", "customer_unique_id",
                                "customer_zip_code_prefix",
                                "customer_city", "customer_state"]]
               for c in customers])

    write_csv(RAW / "olist_sellers_dataset.csv",
              ["seller_id", "seller_zip_code_prefix",
               "seller_city", "seller_state"],
              [[s[k] for k in ["seller_id", "seller_zip_code_prefix",
                                "seller_city", "seller_state"]]
               for s in sellers])

    write_csv(RAW / "olist_products_dataset.csv",
              ["product_id", "product_category_name",
               "product_name_lenght", "product_description_lenght",
               "product_photos_qty", "product_weight_g",
               "product_length_cm", "product_height_cm",
               "product_width_cm"],
              [[p[k] for k in ["product_id", "product_category_name",
                                "product_name_lenght", "product_description_lenght",
                                "product_photos_qty", "product_weight_g",
                                "product_length_cm", "product_height_cm",
                                "product_width_cm"]]
               for p in products])

    write_csv(RAW / "olist_orders_dataset.csv",
              ["order_id", "customer_id", "order_status",
               "order_purchase_timestamp", "order_approved_at",
               "order_delivered_carrier_date", "order_delivered_customer_date",
               "order_estimated_delivery_date"],
              [[o[k] for k in ["order_id", "customer_id", "order_status",
                                "order_purchase_timestamp", "order_approved_at",
                                "order_delivered_carrier_date",
                                "order_delivered_customer_date",
                                "order_estimated_delivery_date"]]
               for o in orders])

    write_csv(RAW / "olist_order_items_dataset.csv",
              ["order_id", "order_item_id", "product_id", "seller_id",
               "shipping_limit_date", "price", "freight_value"],
              [[i[k] for k in ["order_id", "order_item_id", "product_id",
                                "seller_id", "shipping_limit_date",
                                "price", "freight_value"]]
               for i in items])

    write_csv(RAW / "olist_order_payments_dataset.csv",
              ["order_id", "payment_sequential", "payment_type",
               "payment_installments", "payment_value"],
              [[p[k] for k in ["order_id", "payment_sequential",
                                "payment_type", "payment_installments",
                                "payment_value"]]
               for p in payments])

    write_csv(RAW / "olist_order_reviews_dataset.csv",
              ["review_id", "order_id", "review_score",
               "review_comment_title", "review_comment_message",
               "review_creation_date", "review_answer_timestamp"],
              [[r[k] for k in ["review_id", "order_id", "review_score",
                                "review_comment_title", "review_comment_message",
                                "review_creation_date", "review_answer_timestamp"]]
               for r in reviews])

    write_csv(RAW / "product_category_name_translation.csv",
              ["product_category_name", "product_category_name_english"],
              [[k, v] for k, v in CATEGORY_TRANSLATION.items()])

    print(f"\nDone. Tables written under {RAW.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()

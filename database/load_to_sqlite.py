import os
import sqlite3
import numpy as np
import pandas as pd


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DB_PATH = os.path.join(BASE_DIR, "olist.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")


def read_csv_safe(filename):
    """Read a CSV with encoding fallback (Windows default is often gbk/cp1252)."""
    path = os.path.join(PROJECT_ROOT, filename)
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, encoding="latin-1")


def main():
    # ---- Load source CSVs (keep original olist file names) ----
    customers   = read_csv_safe("data/olist_customers_dataset.csv")
    geolocation = read_csv_safe("data/olist_geolocation_dataset.csv")
    items       = read_csv_safe("data/olist_order_items_dataset.csv")
    payments    = read_csv_safe("data/olist_order_payments_dataset.csv")
    reviews     = read_csv_safe("data/olist_order_reviews_dataset.csv")
    orders      = read_csv_safe("data/olist_orders_dataset.csv")
    products    = read_csv_safe("data/olist_products_dataset.csv")
    sellers     = read_csv_safe("data/olist_sellers_dataset.csv")
    category    = read_csv_safe("data/product_category_name_translation.csv")

    # ---- 1. geolocation: one aggregated representative row per zip prefix ----
    geo = (geolocation
           .groupby("geolocation_zip_code_prefix", as_index=False)
           .agg(avg_lat=("geolocation_lat", "mean"),
                avg_lng=("geolocation_lng", "mean"),
                city=("geolocation_city", "first"),
                state=("geolocation_state", "first"))
           .rename(columns={"geolocation_zip_code_prefix": "zip_code_prefix"}))

    # add placeholder zip codes referenced by customers/sellers but missing in geo
    extra = {}
    for z in set(customers["customer_zip_code_prefix"].dropna().unique()) - set(geo["zip_code_prefix"]):
        row = customers[customers["customer_zip_code_prefix"] == z].iloc[0]
        extra[z] = (z, np.nan, np.nan, row["customer_city"], row["customer_state"])
    for z in set(sellers["seller_zip_code_prefix"].dropna().unique()) - set(geo["zip_code_prefix"]):
        if z not in extra:
            row = sellers[sellers["seller_zip_code_prefix"] == z].iloc[0]
            extra[z] = (z, np.nan, np.nan, row["seller_city"], row["seller_state"])
    if extra:
        geo = pd.concat([geo, pd.DataFrame(list(extra.values()), columns=geo.columns)],
                        ignore_index=True)

    # ---- 2. customer_profile (natural person) ----
    profile = customers[["customer_unique_id"]].drop_duplicates()

    # ---- 3. customer ----
    customer = customers.rename(columns={"customer_zip_code_prefix": "zip_code_prefix"})[
        ["customer_id", "customer_unique_id", "zip_code_prefix"]]

    # ---- 4. seller ----
    seller = sellers.rename(columns={"seller_zip_code_prefix": "zip_code_prefix"})[
        ["seller_id", "zip_code_prefix"]]

    # ---- 5. product_category (include unmapped categories found in products) ----
    cat = category
    prod_cats = set(products["product_category_name"].dropna().unique())
    known = set(cat["product_category_name"].unique())
    for c in prod_cats - known:
        cat = pd.concat([cat, pd.DataFrame(
            {"product_category_name": [c], "product_category_name_english": [np.nan]})],
            ignore_index=True)

    # ---- 6. product ----
    product = products.rename(columns={
        "product_name_lenght": "product_name_length",
        "product_description_lenght": "product_description_length"})[[
        "product_id", "product_category_name", "product_name_length",
        "product_description_length", "product_photos_qty", "product_weight_g",
        "product_length_cm", "product_height_cm", "product_width_cm"]]

    # ---- 7. orders ----
    orders_db = orders[[
        "order_id", "customer_id", "order_status", "order_purchase_timestamp",
        "order_approved_at", "order_delivered_carrier_date",
        "order_delivered_customer_date", "order_estimated_delivery_date"]]

    # ---- 8. order_item ----
    item = items[[
        "order_id", "order_item_id", "product_id", "seller_id",
        "shipping_limit_date", "price", "freight_value"]]

    # ---- 9. payment ----
    payment = payments[[
        "order_id", "payment_sequential", "payment_type",
        "payment_installments", "payment_value"]]

    # ---- 10. review (surrogate key row number) ----
    review = reviews.copy().reset_index(drop=True)
    review.insert(0, "review_pk", review.index + 1)
    review = review[[
        "review_pk", "review_id", "order_id", "review_score",
        "review_comment_title", "review_comment_message",
        "review_creation_date", "review_answer_timestamp"]]

    # ---- Write to SQLite ----
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    con = sqlite3.connect(DB_PATH)
    con.executescript(open(SCHEMA_PATH, "r", encoding="utf-8").read())

    geo.to_sql("geolocation", con, if_exists="append", index=False)
    profile.to_sql("customer_profile", con, if_exists="append", index=False)
    customer.to_sql("customer", con, if_exists="append", index=False)
    seller.to_sql("seller", con, if_exists="append", index=False)
    cat.to_sql("product_category", con, if_exists="append", index=False)
    product.to_sql("product", con, if_exists="append", index=False)
    orders_db.to_sql("orders", con, if_exists="append", index=False)
    item.to_sql("order_item", con, if_exists="append", index=False)
    payment.to_sql("payment", con, if_exists="append", index=False)
    review.to_sql("review", con, if_exists="append", index=False)
    con.commit()

    # ---- Verification ----
    print("=== Row counts loaded ===")
    for t in ["geolocation", "customer_profile", "customer", "seller",
              "product_category", "product", "orders", "order_item",
              "payment", "review"]:
        n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t:20s} {n}")

    orphans = [
        ("orders", "customer_id", "customer", "customer_id"),
        ("order_item", "order_id", "orders", "order_id"),
        ("order_item", "product_id", "product", "product_id"),
        ("order_item", "seller_id", "seller", "seller_id"),
        ("payment", "order_id", "orders", "order_id"),
        ("review", "order_id", "orders", "order_id"),
    ]
    print("\n=== Orphan FK rows (should be 0) ===")
    for ch, ck, par, pk in orphans:
        q = f"""SELECT COUNT(*) FROM {ch} c LEFT JOIN {par} p ON c.{ck}=p.{pk}
                WHERE p.{pk} IS NULL"""
        print(f"  {ch}.{ck} -> {par}: {con.execute(q).fetchone()[0]}")

    con.close()
    print(f"\nDatabase saved: {DB_PATH}")


if __name__ == "__main__":
    main()

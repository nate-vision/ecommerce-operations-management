import os
import sqlite3
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---- Cross-platform paths ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
DB_PATH = os.path.join(PROJECT_ROOT, "database", "olist.db")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results", "seller")
CHARTS = os.path.join(RESULTS_DIR, "charts")
os.makedirs(CHARTS, exist_ok=True)

# Font setup: SimHei on Windows, DejaVu Sans elsewhere; keep minus sign readable
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["axes.grid"] = True
plt.rcParams["grid.alpha"] = 0.3

con = sqlite3.connect(DB_PATH)

# ---- Seller performance metrics (same logic as seller_module.sql view) ----
metrics = pd.read_sql(
    """
    WITH item_agg AS (
        SELECT i.seller_id,
               COUNT(DISTINCT i.order_id)            AS total_orders,
               COUNT(*)                              AS total_items,
               ROUND(SUM(i.price), 2)                 AS gross_revenue,
               ROUND(SUM(i.freight_value), 2)         AS total_freight,
               ROUND(AVG(i.price), 2)                 AS avg_item_price,
               COUNT(DISTINCT i.product_id)          AS distinct_products,
               MIN(o.order_purchase_timestamp)       AS first_order_date,
               MAX(o.order_purchase_timestamp)       AS last_order_date
        FROM order_item i JOIN orders o ON i.order_id = o.order_id
        GROUP BY i.seller_id
    ),
    review_agg AS (
        SELECT i.seller_id,
               ROUND(AVG(r.review_score), 2)  AS avg_review_score,
               COUNT(r.review_pk)             AS review_count
        FROM order_item i JOIN review r ON i.order_id = r.order_id
        GROUP BY i.seller_id
    )
    SELECT s.seller_id, g.state, g.city,
           ia.total_orders, ia.total_items, ia.gross_revenue, ia.total_freight,
           ia.avg_item_price, ia.distinct_products,
           COALESCE(ra.avg_review_score, 0) AS avg_review_score,
           COALESCE(ra.review_count, 0)       AS review_count,
           ia.first_order_date, ia.last_order_date
    FROM seller s
    LEFT JOIN geolocation g ON s.zip_code_prefix = g.zip_code_prefix
    LEFT JOIN item_agg  ia ON s.seller_id = ia.seller_id
    LEFT JOIN review_agg ra ON s.seller_id = ra.seller_id
    """, con)

metrics["gross_revenue"] = metrics["gross_revenue"].fillna(0)
metrics["total_orders"] = metrics["total_orders"].fillna(0).astype(int)
metrics.to_csv(os.path.join(RESULTS_DIR, "seller_metrics.csv"), index=False,
               encoding="utf-8-sig")

# ---- Headline numbers ----
total_sellers = len(metrics)
active = (metrics["total_orders"] > 0).sum()
total_rev = metrics["gross_revenue"].sum()
top10 = metrics.nlargest(10, "gross_revenue")
top10_share = top10["gross_revenue"].sum() / total_rev * 100
median_rev = metrics["gross_revenue"].median()
mean_rev = metrics["gross_revenue"].mean()
rated = metrics[metrics["review_count"] > 0]

print("===== Seller Metrics =====")
print(f"Total sellers: {total_sellers}")
print(f"Active sellers (>=1 order): {active} ({active/total_sellers*100:.2f}%)")
print(f"Total gross revenue: R$ {total_rev:,.2f}")
print(f"Mean revenue/seller: R$ {mean_rev:,.2f} | median: R$ {median_rev:,.2f}")
print(f"Top 10 sellers revenue share: {top10_share:.2f}%")
print(f"Sellers with reviews: {len(rated)} | mean avg score: {rated['avg_review_score'].mean():.2f}")

# ---- Chart 1: sellers by state (top 10) ----
by_state = metrics.groupby("state").size().sort_values(ascending=False).head(10)
fig, ax = plt.subplots(figsize=(9, 5))
ax.bar(by_state.index, by_state.values, color="#3b6ea5")
ax.set_title("Number of Sellers by State (Top 10)")
ax.set_xlabel("State (Brazil)"); ax.set_ylabel("Seller count")
for i, v in enumerate(by_state.values):
    ax.text(i, v + 15, str(v), ha="center", fontsize=9)
fig.tight_layout(); fig.savefig(os.path.join(CHARTS, "chart1_sellers_by_state.png"), dpi=150)
plt.close(fig)

# ---- Chart 2: top 10 sellers by revenue ----
t = top10.copy()
t["short"] = t["seller_id"].str[:8]
fig, ax = plt.subplots(figsize=(10, 5.5))
ax.barh(t["short"][::-1], t["gross_revenue"][::-1], color="#2e8b74")
ax.set_title("Top 10 Sellers by Gross Revenue (R$)")
ax.set_xlabel("Gross revenue (R$)"); ax.set_ylabel("Seller ID (first 8 chars)")
for i, v in enumerate(t["gross_revenue"][::-1]):
    ax.text(v, i, f" R$ {v:,.0f}", va="center", fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(CHARTS, "chart2_top10_sellers.png"), dpi=150)
plt.close(fig)

# ---- Chart 3: revenue tiers ----
bins = [-0.01, 0, 1000, 5000, 10000, 50000, np.inf]
labels = ["0 (no sales)", "<1k", "1k–5k", "5k–10k", "10k–50k", "≥50k"]
metrics["tier"] = pd.cut(metrics["gross_revenue"], bins=bins, labels=labels)
tier = metrics.groupby("tier", observed=False).size()
fig, ax = plt.subplots(figsize=(9, 5))
ax.bar(tier.index.astype(str), tier.values, color="#c97b3c")
ax.set_title("Seller Revenue Distribution (R$ tiers)")
ax.set_ylabel("Seller count"); ax.set_xlabel("Revenue tier")
for i, v in enumerate(tier.values):
    ax.text(i, v + 20, str(v), ha="center", fontsize=9)
fig.tight_layout(); fig.savefig(os.path.join(CHARTS, "chart3_revenue_tiers.png"), dpi=150)
plt.close(fig)

# ---- Chart 4: average review score distribution ----
fig, ax = plt.subplots(figsize=(9, 5))
ax.hist(rated["avg_review_score"], bins=np.arange(0.5, 5.6, 0.5),
        color="#7a6fb0", edgecolor="white")
ax.set_title("Distribution of Sellers by Average Review Score")
ax.set_xlabel("Average review score (1–5)"); ax.set_ylabel("Seller count")
fig.tight_layout(); fig.savefig(os.path.join(CHARTS, "chart4_score_distribution.png"), dpi=150)
plt.close(fig)

# ---- Chart 5: monthly active sellers + revenue ----
monthly = pd.read_sql(
    """
    SELECT STRFTIME('%Y-%m', o.order_purchase_timestamp) AS month,
           COUNT(DISTINCT i.seller_id) AS active_sellers,
           ROUND(SUM(i.price), 2)      AS monthly_revenue
    FROM order_item i JOIN orders o ON i.order_id = o.order_id
    GROUP BY month ORDER BY month
    """, con)
fig, ax1 = plt.subplots(figsize=(10, 5))
ax1.bar(monthly["month"], monthly["active_sellers"], color="#9db8d2", label="Active sellers")
ax1.set_ylabel("Active sellers", color="#3b6ea5")
ax2 = ax1.twinx()
ax2.plot(monthly["month"], monthly["monthly_revenue"], color="#c0392b",
         marker="o", ms=3, label="Monthly revenue")
ax2.set_ylabel("Monthly revenue (R$)", color="#c0392b")
ax1.set_title("Monthly Active Sellers and Revenue Trend")
ax1.set_xlabel("Month")
tick_idx = list(range(0, len(monthly), 2))
ax1.set_xticks(monthly["month"].iloc[tick_idx])
plt.xticks(rotation=45, ha="right", fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(CHARTS, "chart5_monthly_trend.png"), dpi=150)
plt.close(fig)

# ---- Per-state summary ----
state_rev = metrics.groupby("state").agg(
    sellers=("seller_id", "size"),
    revenue=("gross_revenue", "sum"),
    avg_score=("avg_review_score", "mean")).sort_values("sellers", ascending=False)
state_rev["revenue"] = state_rev["revenue"].round(2)
state_rev["avg_score"] = state_rev["avg_score"].round(2)
state_rev.to_csv(os.path.join(RESULTS_DIR, "seller_by_state.csv"), encoding="utf-8-sig")

con.close()
print("\nDone: seller_metrics.csv, seller_by_state.csv and charts/ saved.")

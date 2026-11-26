-- V1. Seller performance view (one row per seller)
DROP VIEW IF EXISTS v_seller_performance;
CREATE VIEW v_seller_performance AS
WITH item_agg AS (
    SELECT
        i.seller_id,
        COUNT(DISTINCT i.order_id)              AS total_orders,
        COUNT(*)                                AS total_items,
        ROUND(SUM(i.price), 2)                  AS gross_revenue,
        ROUND(SUM(i.freight_value), 2)          AS total_freight,
        ROUND(AVG(i.price), 2)                  AS avg_item_price,
        COUNT(DISTINCT i.product_id)             AS distinct_products,
        MIN(o.order_purchase_timestamp)         AS first_order_date,
        MAX(o.order_purchase_timestamp)         AS last_order_date
    FROM order_item i
    JOIN orders o ON i.order_id = o.order_id
    GROUP BY i.seller_id
),
review_agg AS (
    SELECT
        i.seller_id,
        ROUND(AVG(r.review_score), 2)           AS avg_review_score,
        COUNT(r.review_pk)                        AS review_count
    FROM order_item i
    JOIN review r ON i.order_id = r.order_id
    GROUP BY i.seller_id
)
SELECT
    s.seller_id,
    g.state,
    g.city,
    ia.total_orders,
    ia.total_items,
    ia.gross_revenue,
    ia.total_freight,
    ia.avg_item_price,
    ia.distinct_products,
    COALESCE(ra.avg_review_score, 0)          AS avg_review_score,
    COALESCE(ra.review_count, 0)               AS review_count,
    ia.first_order_date,
    ia.last_order_date
FROM seller s
LEFT JOIN geolocation g ON s.zip_code_prefix = g.zip_code_prefix
LEFT JOIN item_agg  ia ON s.seller_id = ia.seller_id
LEFT JOIN review_agg ra ON s.seller_id = ra.seller_id;

-- Q1. Top 10 sellers by gross revenue
SELECT seller_id, state, total_orders, total_items, gross_revenue, avg_review_score
FROM v_seller_performance
ORDER BY gross_revenue DESC
LIMIT 10;

-- Q2. Sellers per state: count, total revenue, average score
SELECT state,
       COUNT(*)                            AS seller_count,
       ROUND(SUM(gross_revenue), 2)        AS state_revenue,
       ROUND(AVG(avg_review_score), 2)     AS state_avg_score
FROM v_seller_performance
GROUP BY state
ORDER BY seller_count DESC;

-- Q3. Seller revenue distribution (size tiers)
SELECT
    CASE
        WHEN gross_revenue IS NULL OR gross_revenue = 0 THEN '0_no_sales'
        WHEN gross_revenue < 1000    THEN '1_<1k'
        WHEN gross_revenue < 5000    THEN '2_1k-5k'
        WHEN gross_revenue < 10000   THEN '3_5k-10k'
        WHEN gross_revenue < 50000  THEN '4_10k-50k'
        ELSE '5_>=50k'
    END AS revenue_tier,
    COUNT(*) AS seller_count,
    ROUND(SUM(gross_revenue), 2) AS tier_revenue
FROM v_seller_performance
GROUP BY revenue_tier
ORDER BY revenue_tier;

-- Q4. High-volume but low-rated sellers (>=20 orders, avg score < 3)
SELECT seller_id, state, total_orders, gross_revenue, avg_review_score
FROM v_seller_performance
WHERE total_orders >= 20 AND avg_review_score < 3
ORDER BY total_orders DESC;

-- Q5. Active sellers (at least one order) and their share
SELECT COUNT(*) AS active_sellers,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM seller), 2) AS active_share_pct
FROM v_seller_performance
WHERE total_orders > 0;

-- Q6. Monthly active sellers and revenue (trend)
SELECT STRFTIME('%Y-%m', o.order_purchase_timestamp) AS month,
       COUNT(DISTINCT i.seller_id)                   AS active_sellers,
       ROUND(SUM(i.price), 2)                         AS monthly_revenue
FROM order_item i
JOIN orders o ON i.order_id = o.order_id
GROUP BY month
ORDER BY month;

-- Q7. Revenue concentration: share held by the top 10% sellers
WITH ranked AS (
    SELECT seller_id, gross_revenue,
           PERCENT_RANK() OVER (ORDER BY gross_revenue DESC) AS pr
    FROM v_seller_performance
    WHERE gross_revenue > 0
)
SELECT ROUND(100.0 * SUM(CASE WHEN pr <= 0.10 THEN gross_revenue ELSE 0 END)
      / SUM(gross_revenue), 2) AS top10pct_revenue_share_pct
FROM ranked;

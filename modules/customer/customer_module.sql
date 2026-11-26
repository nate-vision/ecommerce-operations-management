-- SDSC5003 | B: Customer Management and Order History
-- SQLite; uses the original schema.sql and olist.db delivered by A.
-- Read-only: all six queries are SELECT statements. No schema or index changes.
-- Run one numbered query at a time in DB Browser for SQLite (Execute SQL).
-- Replace example literals as needed. Application code should bind parameters.
-- Customer identity: customer_unique_id, not the per-order customer_id.
-- Location: latest order-associated customer record; ties resolved by IDs.
-- Amounts: BRL; order history includes all statuses. Delivered spend uses only
-- recorded payments for delivered orders; it is not net revenue or settlement.

-- Q1. Customer list (20 records per page)
-- Page customer IDs first, then retrieve location and order count for that page.
-- Change OFFSET to 20, 40, ... for later pages.
WITH customer_page AS (
    SELECT customer_unique_id
    FROM customer_profile
    ORDER BY customer_unique_id
    LIMIT 20 OFFSET 0
)
SELECT
    p.customer_unique_id,
    g.city,
    g.state,
    (
        SELECT COUNT(o.order_id)
        FROM customer c2
        JOIN orders o ON o.customer_id = c2.customer_id
        WHERE c2.customer_unique_id = p.customer_unique_id
    ) AS total_orders
FROM customer_page p
LEFT JOIN customer c ON c.customer_id = (
    SELECT c1.customer_id
    FROM customer c1
    LEFT JOIN orders o1 ON o1.customer_id = c1.customer_id
    WHERE c1.customer_unique_id = p.customer_unique_id
    ORDER BY o1.order_purchase_timestamp DESC, o1.order_id DESC,
             c1.customer_id DESC
    LIMIT 1
)
LEFT JOIN geolocation g ON g.zip_code_prefix = c.zip_code_prefix
ORDER BY p.customer_unique_id;

-- Q2. Search and filter customers, then paginate.
-- GLOB prefix search uses the existing customer_profile primary-key index.
-- Use '8d50f5*' for a prefix, or the full ID without * for an exact match.
-- IDs are lowercase hexadecimal. Use '*' for all IDs.
-- Remove the state predicate for all states; optionally add AND g.city = 'sao paulo'.
-- Region means latest order-associated location, consistent with Q1.
WITH matched_page AS (
    SELECT p.customer_unique_id, g.city, g.state
    FROM customer_profile p
    LEFT JOIN customer c ON c.customer_id = (
        SELECT c1.customer_id
        FROM customer c1
        LEFT JOIN orders o1 ON o1.customer_id = c1.customer_id
        WHERE c1.customer_unique_id = p.customer_unique_id
        ORDER BY o1.order_purchase_timestamp DESC, o1.order_id DESC,
                 c1.customer_id DESC
        LIMIT 1
    )
    LEFT JOIN geolocation g ON g.zip_code_prefix = c.zip_code_prefix
    WHERE p.customer_unique_id GLOB '8d50f5*'
      AND g.state = 'SP'
    ORDER BY p.customer_unique_id
    LIMIT 20 OFFSET 0
)
SELECT p.customer_unique_id, p.city, p.state,
    (
        SELECT COUNT(o.order_id)
        FROM customer c2
        JOIN orders o ON o.customer_id = c2.customer_id
        WHERE c2.customer_unique_id = p.customer_unique_id
    ) AS total_orders
FROM matched_page p
ORDER BY p.customer_unique_id;

-- Q3. Customer details (one row for an existing identity)
-- Latest observed order location is not a verified current address.
SELECT p.customer_unique_id, c.customer_id AS latest_customer_id,
       g.zip_code_prefix, g.city, g.state,
       g.avg_lat, g.avg_lng,
       (
           SELECT MIN(o2.order_purchase_timestamp)
           FROM customer c2
           JOIN orders o2 ON o2.customer_id = c2.customer_id
           WHERE c2.customer_unique_id = p.customer_unique_id
       ) AS first_order_date,
       o.order_purchase_timestamp AS latest_order_date
FROM customer_profile p
LEFT JOIN orders o ON o.order_id = (
    SELECT o1.order_id
    FROM customer c1
    JOIN orders o1 ON o1.customer_id = c1.customer_id
    WHERE c1.customer_unique_id = p.customer_unique_id
    ORDER BY o1.order_purchase_timestamp DESC, o1.order_id DESC
    LIMIT 1
)
LEFT JOIN customer c ON c.customer_id = COALESCE(o.customer_id, (
    SELECT c3.customer_id FROM customer c3
    WHERE c3.customer_unique_id = p.customer_unique_id
    ORDER BY c3.customer_id DESC LIMIT 1
))
LEFT JOIN geolocation g ON g.zip_code_prefix = c.zip_code_prefix
WHERE p.customer_unique_id = '8d50f5eadf50201ccdcedfb9e2ac8455';

-- Q4. All historical orders of one customer (one row per order)
-- Sum payments at order level; do not join payment and order_item directly.
-- NULL payment_amount means no recorded non-null payment amount.
SELECT o.order_id, o.order_purchase_timestamp, o.order_status,
       o.order_estimated_delivery_date, o.order_delivered_customer_date,
       g.city, g.state,
       (
           SELECT ROUND(SUM(p.payment_value), 2)
           FROM payment p WHERE p.order_id = o.order_id
       ) AS payment_amount
FROM customer c
JOIN orders o ON o.customer_id = c.customer_id
LEFT JOIN geolocation g ON g.zip_code_prefix = c.zip_code_prefix
WHERE c.customer_unique_id = '8d50f5eadf50201ccdcedfb9e2ac8455'
ORDER BY o.order_purchase_timestamp DESC, o.order_id DESC;

-- Q5. Customer order and spending summary (one row per existing identity)
-- Count all orders, count delivered orders, sum only delivered payments.
-- Missing-payment count makes the spending coverage explicit.
WITH customer_history AS (
    SELECT o.order_id, o.order_status,
           CASE WHEN o.order_status = 'delivered' THEN (
               SELECT SUM(p.payment_value)
               FROM payment p WHERE p.order_id = o.order_id
           ) END AS delivered_payment
    FROM customer c
    JOIN orders o ON o.customer_id = c.customer_id
    WHERE c.customer_unique_id = '8d50f5eadf50201ccdcedfb9e2ac8455'
)
SELECT p.customer_unique_id,
       COUNT(h.order_id) AS total_orders,
       COUNT(CASE WHEN h.order_status = 'delivered' THEN 1 END) AS delivered_orders,
       ROUND(COALESCE(SUM(h.delivered_payment), 0), 2) AS delivered_spend,
       COUNT(CASE WHEN h.order_status = 'delivered'
                       AND h.delivered_payment IS NULL THEN 1 END)
           AS delivered_orders_missing_payment
FROM customer_profile p
LEFT JOIN customer_history h ON 1 = 1
WHERE p.customer_unique_id = '8d50f5eadf50201ccdcedfb9e2ac8455'
GROUP BY p.customer_unique_id;

-- Q6. Order item details (only if the order belongs to the requested customer)
-- Product and shipping amounts are item-level, not order-level payment totals.
SELECT i.order_item_id, i.product_id, i.seller_id,
       pr.product_category_name,
       pc.product_category_name_english,
       ROUND(i.price, 2) AS price,
       ROUND(i.freight_value, 2) AS freight_value,
       ROUND(i.price + i.freight_value, 2) AS item_total
FROM orders o
JOIN customer c ON c.customer_id = o.customer_id
JOIN order_item i ON i.order_id = o.order_id
JOIN product pr ON pr.product_id = i.product_id
LEFT JOIN product_category pc
    ON pc.product_category_name = pr.product_category_name
WHERE o.order_id = 'd3582fd5ccccd9cb229a63dfb417c86f'
  AND c.customer_unique_id = '8d50f5eadf50201ccdcedfb9e2ac8455'
ORDER BY i.order_item_id;

-- Evaluation: prepend EXPLAIN QUERY PLAN to any complete SELECT/WITH above.
-- Q1 comparison baseline (same output and location rule, global window ranking):
/*
WITH ranked_customers AS (
    SELECT c.customer_unique_id, c.zip_code_prefix,
           ROW_NUMBER() OVER (
               PARTITION BY c.customer_unique_id
               ORDER BY o.order_purchase_timestamp DESC, o.order_id DESC,
                        c.customer_id DESC
           ) AS rn,
           COUNT(o.order_id) OVER (
               PARTITION BY c.customer_unique_id
           ) AS total_orders
    FROM customer c
    LEFT JOIN orders o ON c.customer_id = o.customer_id
)
SELECT p.customer_unique_id, g.city, g.state,
       COALESCE(r.total_orders, 0) AS total_orders
FROM customer_profile p
LEFT JOIN ranked_customers r
    ON p.customer_unique_id = r.customer_unique_id AND r.rn = 1
LEFT JOIN geolocation g ON g.zip_code_prefix = r.zip_code_prefix
ORDER BY p.customer_unique_id
LIMIT 20 OFFSET 0;
*/

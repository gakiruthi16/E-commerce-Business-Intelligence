SELECT 'order' AS table_name, COUNT(*) AS total_rows FROM orders
UNION ALL
SELECT 'order_item' AS table_name, COUNT(*) AS total_rows FROM order_items
UNION ALL
SELECT 'products' AS table_name, COUNT(*) AS total_rows FROM products;

SELECT
    order_status,
    COUNT(*) AS total_orders
FROM orders
GROUP BY order_status
ORDER BY total_orders DESC;

SELECT
    COUNT(*) AS total_orders,
    COUNT(order_purchase_timestamp) AS orders_with_purchase_date,
    COUNT(order_delivered_customer_date) AS orders_with_delivery_date,
    COUNT(order_estimated_delivery_date) AS orders_with_estimated_date
FROM orders;

SELECT
    ROUND(SUM(o1.price)::numeric, 2) AS total_revenue,
    COUNT(DISTINCT o.order_id) AS delivered_orders
FROM orders o
INNER JOIN order_items o1
    ON o.order_id = o1.order_id
WHERE o.order_status = 'delivered';

SELECT
    TO_CHAR(
        DATE_TRUNC('month', o.order_purchase_timestamp::timestamp),
        'FMMonth YYYY'
    ) AS month,
    ROUND(SUM(o1.price)::numeric, 2) AS month_revenue
FROM orders o
INNER JOIN order_items o1
    ON o.order_id = o1.order_id
WHERE o.order_status = 'delivered'
GROUP BY DATE_TRUNC('month', o.order_purchase_timestamp::timestamp)
ORDER BY DATE_TRUNC('month', o.order_purchase_timestamp::timestamp);

SELECT
    p.product_category_name,
    ROUND(SUM(o1.price)::numeric, 2) AS product_revenue
FROM order_items o1
INNER JOIN products p
    ON o1.product_id = p.product_id
GROUP BY p.product_category_name
ORDER BY product_revenue DESC;

SELECT
    product_id,
    ROUND(SUM(price)::numeric, 2) AS product_revenue
FROM order_items
GROUP BY product_id
ORDER BY product_revenue DESC
LIMIT 10;

SELECT
    COUNT(*) AS total_delivered_orders,
    COUNT(
        CASE
            WHEN order_delivered_customer_date::timestamp
                 > order_estimated_delivery_date::timestamp
            THEN 1
        END
    ) AS late_delivery,
    ROUND(
        COUNT(
            CASE
                WHEN order_delivered_customer_date::timestamp
                     > order_estimated_delivery_date::timestamp
                THEN 1
            END
        ) * 100.0 / NULLIF(COUNT(*), 0),
        2
    ) AS late_delivery_percentage
FROM orders
WHERE order_status = 'delivered';

SELECT
    p.product_category_name,
    COUNT(DISTINCT o.order_id) AS total_delivered_orders,
    COUNT(
        DISTINCT CASE
            WHEN o.order_delivered_customer_date::timestamp
                 > o.order_estimated_delivery_date::timestamp
            THEN o.order_id
        END
    ) AS late_delivery
FROM orders o
INNER JOIN order_items o1
    ON o.order_id = o1.order_id
INNER JOIN products p
    ON o1.product_id = p.product_id
WHERE o.order_status = 'delivered'
GROUP BY p.product_category_name
ORDER BY late_delivery DESC;

SELECT
    COUNT(DISTINCT o.order_id) AS total_orders,
    ROUND(SUM(o1.price)::numeric, 2) AS total_revenue,
    COUNT(DISTINCT o.customer_id) AS total_customers,
    ROUND(
        SUM(o1.price)::numeric /
        NULLIF(COUNT(DISTINCT o.order_id), 0),
        2
    ) AS average_order_value
FROM orders o
INNER JOIN order_items o1
    ON o.order_id = o1.order_id
WHERE o.order_status = 'delivered';

SELECT
    payment_type,
    COUNT(DISTINCT order_id) AS total_orders,
    ROUND(SUM(payment_value)::numeric, 2) AS total_payment
FROM order_payments
GROUP BY payment_type
ORDER BY total_orders DESC;

SELECT
    review_score,
    COUNT(*) AS total_reviews,
    ROUND(
        COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (),
        2
    ) AS review_percentage
FROM order_reviews
GROUP BY review_score
ORDER BY review_score;
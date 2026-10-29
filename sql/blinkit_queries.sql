-- ================================================================
-- BLINKIT SUPPLY CHAIN — SQL ANALYSIS QUERIES
-- Author  : Rishi Verma  |  Email: verma009rishi19@gmail.com
-- Dataset : Blinkit Grocery & Supply Chain Data (8 tables)
-- Engine  : SQLite (compatible with PostgreSQL / MySQL)
-- Topics  : JOINs, CTEs, Window Functions, CASE WHEN, Subqueries
-- ================================================================


-- ────────────────────────────────────────────────────────────────
-- SECTION 1: REVENUE & SALES ANALYSIS
-- ────────────────────────────────────────────────────────────────

-- Q1: Monthly Revenue Summary with Window Function
SELECT
    order_month_name                                        AS Month,
    order_year                                              AS Year,
    COUNT(DISTINCT order_id)                                AS Total_Orders,
    ROUND(SUM(order_total), 2)                              AS Total_Revenue,
    ROUND(AVG(order_total), 2)                              AS Avg_Order_Value,
    ROUND(SUM(order_total) * 100.0 /
          SUM(SUM(order_total)) OVER (), 2)                 AS Revenue_Share_Pct
FROM orders
GROUP BY order_year, order_month, order_month_name
ORDER BY order_year, order_month;


-- Q2: Top 10 Products by Revenue (JOIN + RANK)
SELECT
    p.product_name,
    p.category,
    p.brand,
    SUM(oi.quantity)                                        AS Total_Units_Sold,
    ROUND(SUM(oi.line_total), 2)                            AS Total_Revenue,
    ROUND(AVG(oi.unit_price), 2)                            AS Avg_Selling_Price,
    RANK() OVER (ORDER BY SUM(oi.line_total) DESC)          AS Revenue_Rank
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
GROUP BY p.product_id, p.product_name, p.category, p.brand
ORDER BY Total_Revenue DESC
LIMIT 10;


-- Q3: Category Revenue with CTE + Running Total
WITH category_revenue AS (
    SELECT
        p.category,
        ROUND(SUM(oi.line_total), 2) AS revenue
    FROM order_items oi
    JOIN products p ON oi.product_id = p.product_id
    GROUP BY p.category
)
SELECT
    category,
    revenue                                                  AS Category_Revenue,
    ROUND(revenue * 100.0 / SUM(revenue) OVER (), 2)        AS Revenue_Share_Pct,
    ROUND(SUM(revenue) OVER (ORDER BY revenue DESC), 2)     AS Running_Total
FROM category_revenue
ORDER BY revenue DESC;


-- Q4: Revenue by Customer Segment (3-table JOIN)
SELECT
    c.customer_segment,
    COUNT(DISTINCT o.order_id)                              AS Total_Orders,
    COUNT(DISTINCT o.customer_id)                           AS Total_Customers,
    ROUND(SUM(o.order_total), 2)                            AS Total_Revenue,
    ROUND(AVG(o.order_total), 2)                            AS Avg_Order_Value,
    ROUND(SUM(o.order_total) /
          COUNT(DISTINCT o.customer_id), 2)                 AS Revenue_Per_Customer
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
GROUP BY c.customer_segment
ORDER BY Total_Revenue DESC;


-- ────────────────────────────────────────────────────────────────
-- SECTION 2: INVENTORY & STOCK ANALYSIS
-- ────────────────────────────────────────────────────────────────

-- Q5: Stock-Out Risk Analysis (CTE + CASE WHEN)
WITH product_demand AS (
    SELECT
        product_id,
        SUM(quantity)              AS total_sold,
        ROUND(AVG(quantity), 2)    AS avg_daily_demand
    FROM order_items
    GROUP BY product_id
)
SELECT
    p.product_name,
    p.category,
    p.min_stock_level,
    p.max_stock_level,
    p.shelf_life_days,
    pd.total_sold,
    pd.avg_daily_demand,
    ROUND(p.min_stock_level /
          NULLIF(pd.avg_daily_demand, 0), 1)                AS days_of_cover,
    CASE
        WHEN p.min_stock_level / NULLIF(pd.avg_daily_demand,0) < 2  THEN 'CRITICAL'
        WHEN p.min_stock_level / NULLIF(pd.avg_daily_demand,0) < 5  THEN 'WARNING'
        ELSE 'SAFE'
    END                                                      AS stock_risk
FROM products p
JOIN product_demand pd ON p.product_id = pd.product_id
ORDER BY days_of_cover ASC
LIMIT 20;


-- Q6: Damaged Stock Financial Loss by Category
SELECT
    p.category,
    SUM(i.stock_received)                                   AS Total_Received,
    SUM(i.damaged_stock)                                    AS Total_Damaged,
    ROUND(SUM(i.damaged_stock) * 100.0 /
          NULLIF(SUM(i.stock_received), 0), 2)              AS Damage_Rate_Pct,
    ROUND(SUM(i.damaged_stock) * AVG(p.price), 2)          AS Estimated_Loss_INR
FROM inventory i
JOIN products p ON i.product_id = p.product_id
GROUP BY p.category
ORDER BY Estimated_Loss_INR DESC;


-- Q7: Monthly Inventory Trend per Category
SELECT
    p.category,
    strftime('%Y-%m', i.date)                               AS Year_Month,
    SUM(i.stock_received)                                   AS Monthly_Received,
    SUM(i.damaged_stock)                                    AS Monthly_Damaged,
    SUM(i.good_stock)                                       AS Monthly_Good_Stock,
    ROUND(AVG(i.damage_rate), 2)                            AS Avg_Damage_Rate
FROM inventory i
JOIN products p ON i.product_id = p.product_id
GROUP BY p.category, Year_Month
ORDER BY p.category, Year_Month;


-- Q8: Slow-Moving / Dead Stock (LEFT JOIN + COALESCE)
WITH sales_agg AS (
    SELECT product_id, SUM(quantity) AS units_sold
    FROM order_items
    GROUP BY product_id
)
SELECT
    p.product_name,
    p.category,
    p.max_stock_level,
    COALESCE(s.units_sold, 0)                               AS Units_Sold,
    p.price,
    ROUND(p.max_stock_level * p.price, 2)                   AS Inventory_Value_At_Risk
FROM products p
LEFT JOIN sales_agg s ON p.product_id = s.product_id
WHERE COALESCE(s.units_sold, 0) < 5
ORDER BY Inventory_Value_At_Risk DESC
LIMIT 15;


-- ────────────────────────────────────────────────────────────────
-- SECTION 3: DELIVERY PERFORMANCE
-- ────────────────────────────────────────────────────────────────

-- Q9: Delivery Performance by Store
SELECT
    o.store_id,
    COUNT(o.order_id)                                       AS Total_Orders,
    SUM(o.is_late)                                          AS Late_Orders,
    ROUND(SUM(o.is_late) * 100.0 / COUNT(*), 1)            AS Late_Pct,
    ROUND(AVG(d.delivery_time_minutes), 1)                  AS Avg_Delivery_Min,
    ROUND(AVG(o.delay_minutes), 1)                          AS Avg_Delay_Min,
    ROUND(SUM(o.order_total), 2)                            AS Store_Revenue
FROM orders o
JOIN delivery d ON o.order_id = d.order_id
GROUP BY o.store_id
ORDER BY Late_Pct DESC
LIMIT 15;


-- Q10: Delivery Status vs Customer Rating & Sentiment
SELECT
    o.delivery_status,
    COUNT(f.feedback_id)                                    AS Total_Feedbacks,
    ROUND(AVG(f.rating), 2)                                 AS Avg_Rating,
    ROUND(AVG(o.delay_minutes), 1)                          AS Avg_Delay_Min,
    SUM(CASE WHEN f.sentiment = 'Positive' THEN 1 ELSE 0 END) AS Positive_Count,
    SUM(CASE WHEN f.sentiment = 'Negative' THEN 1 ELSE 0 END) AS Negative_Count
FROM orders o
JOIN feedback f ON o.order_id = f.order_id
GROUP BY o.delivery_status
ORDER BY Avg_Rating DESC;


-- ────────────────────────────────────────────────────────────────
-- SECTION 4: CUSTOMER ANALYSIS
-- ────────────────────────────────────────────────────────────────

-- Q11: RFM Customer Segmentation (CTE + CASE WHEN)
WITH rfm_base AS (
    SELECT
        o.customer_id,
        c.customer_segment,
        MAX(DATE(o.order_date))                             AS last_order_date,
        JULIANDAY('now') - JULIANDAY(MAX(DATE(o.order_date))) AS recency_days,
        COUNT(DISTINCT o.order_id)                          AS frequency,
        ROUND(SUM(o.order_total), 2)                        AS monetary
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    GROUP BY o.customer_id, c.customer_segment
)
SELECT
    customer_id,
    customer_segment,
    ROUND(recency_days, 0)                                  AS Recency_Days,
    frequency                                               AS Frequency,
    monetary                                                AS Monetary,
    CASE
        WHEN recency_days <= 30  AND frequency >= 3 AND monetary >= 1000 THEN 'Champions'
        WHEN recency_days <= 60  AND frequency >= 2                       THEN 'Loyal'
        WHEN recency_days <= 90                                            THEN 'At Risk'
        ELSE 'Lost'
    END                                                     AS RFM_Segment
FROM rfm_base
ORDER BY monetary DESC;


-- Q12: Top 10 Most Valuable Customers (DENSE_RANK)
SELECT
    c.customer_name,
    c.customer_segment,
    c.area,
    COUNT(DISTINCT o.order_id)                              AS Total_Orders,
    ROUND(SUM(o.order_total), 2)                            AS Lifetime_Value,
    ROUND(AVG(o.order_total), 2)                            AS Avg_Order_Value,
    ROUND(AVG(f.rating), 2)                                 AS Avg_Rating,
    DENSE_RANK() OVER (ORDER BY SUM(o.order_total) DESC)    AS Value_Rank
FROM orders o
JOIN customers c     ON o.customer_id = c.customer_id
LEFT JOIN feedback f ON o.order_id    = f.order_id
GROUP BY o.customer_id, c.customer_name, c.customer_segment, c.area
ORDER BY Lifetime_Value DESC
LIMIT 10;


-- ────────────────────────────────────────────────────────────────
-- SECTION 5: ADVANCED SUPPLY CHAIN
-- ────────────────────────────────────────────────────────────────

-- Q13: Product Profitability Ranking (NTILE Window Function)
SELECT
    p.product_name,
    p.category,
    p.margin_percentage,
    SUM(oi.quantity)                                        AS Units_Sold,
    ROUND(SUM(oi.line_total), 2)                            AS Gross_Revenue,
    ROUND(SUM(oi.line_total) * p.margin_percentage / 100, 2) AS Estimated_Profit,
    NTILE(4) OVER
        (ORDER BY SUM(oi.line_total) * p.margin_percentage / 100 DESC) AS Profit_Quartile
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
GROUP BY p.product_id, p.product_name, p.category, p.margin_percentage
ORDER BY Estimated_Profit DESC
LIMIT 15;


-- Q14: Payment Method by Segment (PARTITION BY)
SELECT
    c.customer_segment,
    o.payment_method,
    COUNT(*)                                                AS Order_Count,
    ROUND(AVG(o.order_total), 2)                            AS Avg_Order_Value,
    ROUND(COUNT(*) * 100.0 /
          SUM(COUNT(*)) OVER
              (PARTITION BY c.customer_segment), 1)         AS Pct_Within_Segment
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
GROUP BY c.customer_segment, o.payment_method
ORDER BY c.customer_segment, Order_Count DESC;


-- Q15: Marketing Channel Efficiency Scorecard
SELECT
    channel,
    COUNT(campaign_id)                                      AS Campaigns,
    ROUND(SUM(spend), 2)                                    AS Total_Spend,
    ROUND(SUM(revenue_generated), 2)                        AS Total_Revenue,
    ROUND(SUM(revenue_generated) /
          NULLIF(SUM(spend), 0), 2)                         AS Overall_ROAS,
    ROUND(AVG(ctr), 2)                                      AS Avg_CTR_Pct,
    ROUND(AVG(conversion_rate), 2)                          AS Avg_Conv_Rate_Pct,
    SUM(conversions)                                        AS Total_Conversions,
    ROUND(SUM(spend) /
          NULLIF(SUM(conversions), 0), 2)                   AS Cost_Per_Conversion
FROM marketing
GROUP BY channel
ORDER BY Overall_ROAS DESC;

-- ================================================================
-- END OF SCRIPT
-- ================================================================

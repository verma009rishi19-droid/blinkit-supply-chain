# 📊 Phase 6 — Power BI Dashboard Guide
**Project**: Blinkit Supply Chain & Inventory Optimization  
**Author**: Rishi Verma

---

## 🎯 Dashboard Overview

Build a **6-page interactive Power BI dashboard** from the cleaned CSVs exported in Phase 1–5.

---

## 📁 Files to Import into Power BI

Load these from `data/cleaned/` and `outputs/reports/`:

| File | Used On Page |
|---|---|
| `master_sales.csv` | Page 1, 2, 3 |
| `inventory_cleaned.csv` | Page 4 |
| `products_cleaned.csv` | All pages |
| `delivery_cleaned.csv` | Page 5 |
| `customers_cleaned.csv` | Page 3 |
| `feedback_cleaned.csv` | Page 5 |
| `marketing_cleaned.csv` | Page 6 |
| `abc_classification.csv` | Page 4 |
| `inventory_optimization_report.csv` | Page 4 |
| `demand_forecast_30days.csv` | Page 4 |
| `model_comparison_metrics.csv` | Page 6 |

---

## 🔗 Data Model (Relationships)

```
master_sales
  ├── product_id  →  products_cleaned (product_id)
  ├── order_id    →  delivery_cleaned (order_id)
  ├── order_id    →  feedback_cleaned (order_id)
  └── customer_id →  customers_cleaned (customer_id)

inventory_cleaned
  └── product_id  →  products_cleaned (product_id)

abc_classification
  └── product_id  →  products_cleaned (product_id)
```

---

## 📐 DAX Measures to Create

Paste these in the **Modeling → New Measure** panel:

```dax
-- Total Revenue
Total Revenue = SUM(master_sales[line_total])

-- Average Order Value
Avg Order Value = AVERAGE(orders_cleaned[order_total])

-- Late Delivery %
Late Delivery % = 
DIVIDE(
    COUNTROWS(FILTER(orders_cleaned, orders_cleaned[is_late] = 1)),
    COUNTROWS(orders_cleaned)
) * 100

-- Damage Rate %
Damage Rate % = 
DIVIDE(
    SUM(inventory_cleaned[damaged_stock]),
    SUM(inventory_cleaned[stock_received])
) * 100

-- Total Financial Loss (Damaged Stock)
Total Damage Loss = 
SUMX(
    inventory_optimization_report,
    inventory_optimization_report[financial_loss]
)

-- Products at Stock-Out Risk
At Risk Products = 
COUNTROWS(
    FILTER(inventory_optimization_report,
           inventory_optimization_report[stock_status] = "🔴 Below ROP — Restock NOW")
)

-- Revenue MoM Growth %
Revenue MoM % = 
VAR CurrentMonth = SUM(master_sales[line_total])
VAR PrevMonth = CALCULATE(SUM(master_sales[line_total]),
                           DATEADD('DateTable'[Date], -1, MONTH))
RETURN DIVIDE(CurrentMonth - PrevMonth, PrevMonth) * 100
```

---

## 🖥️ Page-by-Page Dashboard Design

---

### 📄 Page 1 — Executive KPI Summary

**Background color**: Dark navy (`#1a1a2e`) or white  
**Layout**: Top KPI cards → Charts below

#### KPI Cards (top row):
| Card | Measure | Icon |
|---|---|---|
| Total Revenue | `Total Revenue` | 💰 |
| Total Orders | `COUNTROWS(orders_cleaned)` | 🛒 |
| Avg Order Value | `Avg Order Value` | 📦 |
| Late Delivery % | `Late Delivery %` | 🚴 |
| Damage Loss | `Total Damage Loss` | 💥 |
| At-Risk Products | `At Risk Products` | 🔴 |

#### Charts:
- **Line Chart**: Monthly Revenue Trend (`order_month_name` vs `Total Revenue`)
- **Donut Chart**: Orders by `delivery_status`
- **Bar Chart**: Revenue by `category` (top 8)
- **Card**: Date range slicer

---

### 📄 Page 2 — Sales Deep Dive

#### Slicers: `category`, `order_month_name`, `customer_segment`

#### Charts:
- **Clustered Bar**: Top 15 products by revenue
- **Line + Bar (Combo)**: Orders count + Revenue trend by month
- **Treemap**: Revenue share by category
- **Scatter Plot**: `unit_price` vs `quantity` (size = `line_total`)
- **Matrix Table**: Category × Month revenue heatmap

---

### 📄 Page 3 — Customer Analytics

#### Slicers: `customer_segment`, `area`

#### Charts:
- **Bar Chart**: Customer count by `customer_segment`
- **Bar Chart**: Avg Order Value by segment
- **Donut**: Payment method split (`payment_method`)
- **Bar**: Top 10 areas by revenue
- **Table**: Top 20 customers (name, segment, lifetime value, orders, avg rating)
- **Gauge**: Overall avg customer rating (from `feedback_cleaned`)

---

### 📄 Page 4 — Inventory Health 🔑

> **This is the most important supply chain page!**

#### Slicers: `abc_class`, `category`, `is_perishable`

#### Charts:
- **Stacked Bar**: ABC class product count + revenue %
- **Bar Chart (conditional colors)**: Reorder Point vs Min Stock Level  
  *(Red bars = items below ROP)*
- **Line Chart**: Daily stock received vs damaged over time
- **Heatmap (Matrix)**: Category × Month damage rate
- **KPI Cards**:
  - ABC-A Product count
  - Products needing restock NOW
  - Total damaged stock value (₹)
  - Avg EOQ across products
- **Table**: Inventory Optimization Report  
  columns: product, category, abc_class, eoq, reorder_point, stock_status, financial_loss

#### Forecast Section:
- **Line Chart**: 30-day demand forecast by category (from `demand_forecast_30days.csv`)

---

### 📄 Page 5 — Delivery & Feedback

#### Slicers: `delivery_status`, `store_id`

#### Charts:
- **Donut**: Delivery speed buckets (Ultra Fast / Fast / Slow / Very Slow)
- **Bar Chart**: Avg delivery time by store_id (top 10 worst)
- **Bar Chart**: Delay reasons (`reasons_if_delayed`) frequency
- **Scatter**: Avg rating vs avg delay_minutes (store level)
- **Bar Chart**: Avg rating by `delivery_status`
- **Sentiment Cards**: % Positive / Neutral / Negative feedback
- **Rating Distribution**: Bar chart of ratings 1–5

---

### 📄 Page 6 — Marketing Performance

#### Slicers: `channel`, `date` (range)

#### Charts:
- **Bar Chart**: ROAS by marketing channel (with break-even line at 1.0)
- **Clustered Bar**: Spend vs Revenue by channel
- **Line Chart**: Daily revenue trend from marketing (`date` vs `revenue_generated`)
- **KPI Cards**:
  - Total Marketing Spend
  - Total Revenue Generated
  - Overall ROAS
  - Best Performing Channel
- **Scatter**: CTR % vs Conversion Rate (bubble size = spend)
- **Table**: Campaign-level breakdown (campaign_name, channel, spend, revenue, roas, ctr)
- **ML Model Comparison Table** (from `model_comparison_metrics.csv`)

---

## 🎨 Design Tips

| Element | Recommendation |
|---|---|
| **Theme** | Use "Blinkit" colors — Yellow `#F9D923`, Green `#2ECC71`, Dark `#1A1A2E` |
| **Font** | Segoe UI (Power BI default) |
| **Page navigation** | Add buttons on the left sidebar for each page |
| **Tooltips** | Enable rich tooltips with extra product/store detail |
| **Bookmarks** | Create "Stock-Out View" and "High Damage View" bookmarks |
| **Mobile layout** | Use Phone Layout view to make it mobile-friendly |

---

## ✅ Power BI Checklist

- [ ] All 10 CSV files imported and relationships set
- [ ] All DAX measures created
- [ ] Page 1: Executive KPI Summary
- [ ] Page 2: Sales Deep Dive
- [ ] Page 3: Customer Analytics
- [ ] Page 4: Inventory Health ⭐
- [ ] Page 5: Delivery & Feedback
- [ ] Page 6: Marketing Performance
- [ ] Slicers synced across pages
- [ ] Published to Power BI Service (for portfolio link)

---

## 🌐 Publishing for Portfolio

1. Sign in at [app.powerbi.com](https://app.powerbi.com)
2. **Home → Publish** from Power BI Desktop
3. Share the report link in your **README.md** and **LinkedIn**


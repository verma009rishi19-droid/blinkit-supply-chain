# 📦 Blinkit Supply Chain & Inventory Optimization

> End-to-end Data Analytics project using **Python · SQL · Power BI · Machine Learning**

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python) ![SQL](https://img.shields.io/badge/SQL-SQLite-orange?logo=sqlite) ![PowerBI](https://img.shields.io/badge/PowerBI-Dashboard-yellow?logo=powerbi) ![Status](https://img.shields.io/badge/Status-In%20Progress-green)

---

## 📌 Project Overview

This project analyzes **Blinkit's supply chain and inventory data** to derive actionable business insights — identifying stock-out risks, optimizing reorder quantities, analyzing delivery performance, and forecasting demand.

---

## 🗂️ Dataset

| File | Description | Rows |
|---|---|---|
| `blinkit_products.csv` | Product catalog with stock levels & margins | 268 |
| `blinkit_inventory.csv` | Daily stock received & damaged stock | 75,172 |
| `blinkit_orders.csv` | Order-level data with delivery status | 5,000 |
| `blinkit_order_items.csv` | Product-level order line items | 5,000 |
| `blinkit_customers.csv` | Customer profiles & segments | 2,500 |
| `blinkit_delivery_performance.csv` | Delivery time & delay reasons | 5,000 |
| `blinkit_customer_feedback.csv` | Ratings & sentiment data | 5,000 |
| `blinkit_marketing_performance.csv` | Campaign ROI & ROAS | 5,400 |

---

## 🏗️ Project Phases

| Phase | Description | Status |
|---|---|---|
| ✅ Phase 1 | Data Cleaning & Preprocessing | ✅ Complete |
| ✅ Phase 2 | Exploratory Data Analysis (EDA) — 12 charts | ✅ Complete |
| ✅ Phase 3 | SQL Multi-table Analysis — 15 queries | ✅ Complete |
| ✅ Phase 4 | Inventory Optimization (ABC + EOQ + ROP) | ✅ Complete |
| ✅ Phase 5 | Demand Forecasting (ML — RF, XGBoost, LR) | ✅ Complete |
| ✅ Phase 6 | Power BI Dashboard — 6-page guide | ✅ Complete |

---

## 🛠️ Tech Stack

- **Python** — pandas, numpy, matplotlib, seaborn, plotly, scikit-learn, XGBoost
- **SQL** — SQLite via SQLAlchemy
- **Power BI** — Interactive multi-page dashboard
- **Jupyter Notebooks** — for EDA and ML

---

## 📁 Project Structure

```
blinkit-supply-chain/
├── data/
│   ├── raw/               # Original dataset files
│   └── cleaned/           # Cleaned & merged datasets
├── notebooks/
│   ├── 01_data_cleaning.ipynb
│   ├── 02_eda_analysis.ipynb
│   ├── 03_sql_analysis.ipynb
│   ├── 04_inventory_optimization.ipynb
│   └── 05_demand_forecasting.ipynb
├── sql/
│   └── blinkit_queries.sql
├── outputs/
│   ├── charts/            # Saved EDA plots
│   └── reports/           # Summary reports
├── powerbi/
│   └── blinkit_dashboard.pbix
├── requirements.txt
└── README.md
```

---

## 🔑 Key Business Questions Answered

1. Which products are at **stock-out risk**?
2. What is the **optimal reorder quantity** for each category?
3. Which items have the highest **damaged stock wastage**?
4. How does **delivery performance** vary by store/area?
5. What is the **demand forecast** for next 30 days?

---

## 📊 Key Insights Discovered

| # | Insight | Business Impact |
|---|---|---|
| 1 | ABC-A products (≈20% of items) drive **70% of revenue** | Focus tight stock control on A items |
| 2 | Perishable items have **significantly higher damage rates** | Reduce order quantity for short shelf-life products |
| 3 | Late deliveries correlate directly with **lower ratings & negative sentiment** | Prioritize on-time SLA for high-value customers |
| 4 | Multiple products have **min stock below their Reorder Point** — stock-out risk | Trigger immediate replenishment orders |
| 5 | **Fruits & Vegetables** category has the highest damage loss (₹) | Optimize cold chain / delivery frequency |
| 6 | ML best model achieves strong R² on demand prediction | Use forecasts to pre-position stock before weekends |
| 7 | Weekend orders spike — **Saturday has peak demand** | Increase safety stock buffer on Fridays |

## 📁 Output Files Generated

| File | Description |
|---|---|
| `data/cleaned/*.csv` | 10 cleaned datasets ready for analysis |
| `data/blinkit_supplychain.db` | SQLite database with all tables |
| `outputs/charts/` | 19 analysis charts (PNG) |
| `outputs/reports/abc_classification.csv` | ABC class per product |
| `outputs/reports/inventory_optimization_report.csv` | EOQ + ROP + damage loss |
| `outputs/reports/demand_forecast_30days.csv` | 30-day demand forecast |
| `outputs/reports/ml_predictions.csv` | Model test predictions |
| `outputs/reports/model_comparison_metrics.csv` | RMSE, MAE, R² for all models |
| `sql/blinkit_queries.sql` | 15 portfolio-ready SQL queries |
| `powerbi/POWERBI_DASHBOARD_GUIDE.md` | Full 6-page dashboard build guide |

---

## 👤 Author

**Rishi Verma** | Data Analyst  
📧 verma009rishi19@gmail.com

---

## 📄 License

MIT License

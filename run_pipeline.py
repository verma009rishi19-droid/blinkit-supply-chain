"""
run_pipeline.py — Blinkit Supply Chain Full Pipeline
Runs all 5 phases end-to-end and generates all outputs.
Author: Rishi Verma
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # non-interactive backend for script execution
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import sqlite3
import warnings
import os
import sys

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

try:
    from xgboost import XGBRegressor
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

warnings.filterwarnings('ignore')
pd.set_option('display.float_format', '{:.2f}'.format)
sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (14, 6)

# ── PATHS ──────────────────────────────────────────────────────────
BASE      = r"C:\Users\pc\.gemini\antigravity\scratch\blinkit-supply-chain"
DATA_RAW  = r"d:\blinkit project"
CLEANED   = os.path.join(BASE, "data", "cleaned")
CHARTS    = os.path.join(BASE, "outputs", "charts")
REPORTS   = os.path.join(BASE, "outputs", "reports")
DB_PATH   = os.path.join(BASE, "data", "blinkit_supplychain.db")

for d in [CLEANED, CHARTS, REPORTS]:
    os.makedirs(d, exist_ok=True)

def log(msg):
    print(f"\n{'='*60}\n  {msg}\n{'='*60}")

# ══════════════════════════════════════════════════════════════════
# PHASE 1 — DATA CLEANING
# ══════════════════════════════════════════════════════════════════
log("PHASE 1 — DATA CLEANING")

products    = pd.read_csv(f"{DATA_RAW}/blinkit_products.csv")
inventory   = pd.read_csv(f"{DATA_RAW}/blinkit_inventory.csv")
orders      = pd.read_csv(f"{DATA_RAW}/blinkit_orders.csv")
order_items = pd.read_csv(f"{DATA_RAW}/blinkit_order_items.csv")
customers   = pd.read_csv(f"{DATA_RAW}/blinkit_customers.csv")
delivery    = pd.read_csv(f"{DATA_RAW}/blinkit_delivery_performance.csv")
feedback    = pd.read_csv(f"{DATA_RAW}/blinkit_customer_feedback.csv")
marketing   = pd.read_csv(f"{DATA_RAW}/blinkit_marketing_performance.csv")

print(f"  Loaded 8 datasets")

# --- Clean products ---
prod = products.copy().drop_duplicates()
str_cols = prod.select_dtypes('object').columns
prod[str_cols] = prod[str_cols].apply(lambda x: x.str.strip())
prod['category'] = prod['category'].str.title()
prod['brand']    = prod['brand'].str.title()
prod['stock_range']       = prod['max_stock_level'] - prod['min_stock_level']
prod['discount_pct']      = ((prod['mrp'] - prod['price']) / prod['mrp'].replace(0, np.nan) * 100).round(2)
prod['is_perishable']     = prod['shelf_life_days'].apply(lambda x: 'Yes' if x <= 7 else 'No')
prod['revenue_potential'] = (prod['price'] * prod['max_stock_level']).round(2)

# --- Clean inventory ---
inv = inventory.copy().drop_duplicates()
inv['date'] = pd.to_datetime(inv['date'], dayfirst=True)
inv = inv[(inv['stock_received'] >= 0) & (inv['damaged_stock'] >= 0)]
inv = inv[inv['damaged_stock'] <= inv['stock_received']]
inv['good_stock']  = inv['stock_received'] - inv['damaged_stock']
inv['damage_rate'] = (inv['damaged_stock'] / inv['stock_received'].replace(0, np.nan) * 100).round(2)
inv['year']        = inv['date'].dt.year
inv['month']       = inv['date'].dt.month
inv['month_name']  = inv['date'].dt.strftime('%b')
inv['week']        = inv['date'].dt.isocalendar().week.astype(int)
inv['day_of_week'] = inv['date'].dt.day_name()

# --- Clean orders ---
ord_df = orders.copy().drop_duplicates(subset='order_id')
for col in ['order_date','promised_delivery_time','actual_delivery_time']:
    ord_df[col] = pd.to_datetime(ord_df[col])
str_cols = ord_df.select_dtypes('object').columns
ord_df[str_cols] = ord_df[str_cols].apply(lambda x: x.str.strip())
ord_df['order_year']       = ord_df['order_date'].dt.year
ord_df['order_month']      = ord_df['order_date'].dt.month
ord_df['order_month_name'] = ord_df['order_date'].dt.strftime('%b')
ord_df['order_day']        = ord_df['order_date'].dt.day_name()
ord_df['order_hour']       = ord_df['order_date'].dt.hour
ord_df['delay_minutes']    = ((ord_df['actual_delivery_time'] - ord_df['promised_delivery_time'])
                               .dt.total_seconds() / 60).round(2)
ord_df['is_late']          = (ord_df['delay_minutes'] > 0).astype(int)

# --- Clean order items ---
oi = order_items.copy().drop_duplicates()
oi = oi[(oi['quantity'] > 0) & (oi['unit_price'] > 0)]
oi['line_total'] = (oi['quantity'] * oi['unit_price']).round(2)

# --- Clean customers ---
cust = customers.copy().drop_duplicates(subset='customer_id')
cust['registration_date'] = pd.to_datetime(cust['registration_date'])
str_cols = cust.select_dtypes('object').columns
cust[str_cols] = cust[str_cols].apply(lambda x: x.str.strip())
cust['customer_segment'] = cust['customer_segment'].str.title()
cust['tenure_days']      = (pd.Timestamp.now() - cust['registration_date']).dt.days

# --- Clean delivery ---
deliv = delivery.copy().drop_duplicates(subset='order_id')
str_cols = deliv.select_dtypes('object').columns
deliv[str_cols] = deliv[str_cols].apply(lambda x: x.str.strip())
deliv = deliv[deliv['delivery_time_minutes'] > 0]
deliv['delivery_speed'] = pd.cut(
    deliv['delivery_time_minutes'],
    bins=[0,15,30,60,float('inf')],
    labels=['Ultra Fast(<15m)','Fast(15-30m)','Slow(30-60m)','Very Slow(>60m)']
)

# --- Clean feedback ---
fb = feedback.copy().drop_duplicates()
fb['feedback_date'] = pd.to_datetime(fb['feedback_date'])
str_cols = fb.select_dtypes('object').columns
fb[str_cols] = fb[str_cols].apply(lambda x: x.str.strip())
fb['sentiment'] = fb['sentiment'].str.title()
fb['rating']    = fb['rating'].clip(1, 5)

# --- Clean marketing ---
mkt = marketing.copy().drop_duplicates()
mkt['date'] = pd.to_datetime(mkt['date'])
str_cols = mkt.select_dtypes('object').columns
mkt[str_cols] = mkt[str_cols].apply(lambda x: x.str.strip())
mkt['ctr']             = (mkt['clicks'] / mkt['impressions'].replace(0, np.nan) * 100).round(2)
mkt['conversion_rate'] = (mkt['conversions'] / mkt['clicks'].replace(0, np.nan) * 100).round(2)

# --- Master datasets ---
master_sales = (oi
    .merge(prod, on='product_id', how='left')
    .merge(ord_df[['order_id','customer_id','order_date','order_month',
                   'order_month_name','order_day','order_hour',
                   'delivery_status','store_id','is_late','delay_minutes']],
           on='order_id', how='left')
    .merge(cust[['customer_id','area','customer_segment',
                 'total_orders','avg_order_value']],
           on='customer_id', how='left')
)

master_inventory = inv.merge(
    prod[['product_id','product_name','category','price','mrp',
          'min_stock_level','max_stock_level','shelf_life_days',
          'is_perishable','margin_percentage','revenue_potential']],
    on='product_id', how='left'
)

# --- Export cleaned CSVs ---
exports = {
    'products_cleaned.csv'     : prod,
    'inventory_cleaned.csv'    : inv,
    'orders_cleaned.csv'       : ord_df,
    'order_items_cleaned.csv'  : oi,
    'customers_cleaned.csv'    : cust,
    'delivery_cleaned.csv'     : deliv,
    'feedback_cleaned.csv'     : fb,
    'marketing_cleaned.csv'    : mkt,
    'master_sales.csv'         : master_sales,
    'master_inventory.csv'     : master_inventory
}
for fname, df in exports.items():
    df.to_csv(os.path.join(CLEANED, fname), index=False)
    print(f"  ✅ {fname} — {df.shape[0]:,} rows × {df.shape[1]} cols")

print(f"\n  📊 KPIs:")
print(f"  Total Revenue  : ₹{ord_df['order_total'].sum():,.0f}")
print(f"  Total Orders   : {ord_df.shape[0]:,}")
print(f"  Late Orders    : {ord_df['is_late'].sum()} ({ord_df['is_late'].mean()*100:.1f}%)")
print(f"  Avg Damage Rate: {inv['damage_rate'].mean():.2f}%")


# ══════════════════════════════════════════════════════════════════
# PHASE 2 — EDA CHARTS
# ══════════════════════════════════════════════════════════════════
log("PHASE 2 — EDA CHARTS")

# Chart 1: Revenue by Category
cat_rev = master_sales.groupby('category')['line_total'].sum().sort_values(ascending=False)
fig, axes = plt.subplots(1, 2, figsize=(16,7))
axes[0].barh(cat_rev.index, cat_rev.values/1e3, color=sns.color_palette('Set2', len(cat_rev)))
axes[0].set_xlabel('Revenue (₹ Thousands)'); axes[0].set_title('Revenue by Category', fontweight='bold')
axes[1].pie(cat_rev.values, labels=cat_rev.index, autopct='%1.1f%%', startangle=140,
            colors=sns.color_palette('Set2', len(cat_rev)))
axes[1].set_title('Revenue Share %', fontweight='bold')
plt.tight_layout(); plt.savefig(f'{CHARTS}/01_revenue_by_category.png', dpi=150, bbox_inches='tight'); plt.close()
print("  ✅ 01_revenue_by_category.png")

# Chart 2: Monthly Revenue Trend
monthly = ord_df.groupby(['order_year','order_month','order_month_name'])['order_total'].sum().reset_index()
monthly = monthly.sort_values(['order_year','order_month'])
monthly['period'] = monthly['order_month_name'] + ' ' + monthly['order_year'].astype(str)
fig, ax = plt.subplots(figsize=(16,6))
ax.plot(range(len(monthly)), monthly['order_total']/1e3, marker='o', lw=2.5, ms=8, color='#2ecc71')
ax.fill_between(range(len(monthly)), monthly['order_total']/1e3, alpha=0.15, color='#2ecc71')
ax.set_xticks(range(len(monthly))); ax.set_xticklabels(monthly['period'], rotation=45, ha='right')
ax.set_title('Monthly Revenue Trend', fontsize=14, fontweight='bold'); ax.set_ylabel('Revenue (₹K)')
plt.tight_layout(); plt.savefig(f'{CHARTS}/02_monthly_revenue_trend.png', dpi=150, bbox_inches='tight'); plt.close()
print("  ✅ 02_monthly_revenue_trend.png")

# Chart 3: Orders by Day & Hour
fig, axes = plt.subplots(1, 2, figsize=(16,6))
day_order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
day_counts = ord_df['order_day'].value_counts().reindex(day_order)
axes[0].bar(day_counts.index, day_counts.values, color=sns.color_palette('coolwarm',7))
axes[0].set_title('Orders by Day of Week', fontweight='bold'); axes[0].tick_params(axis='x',rotation=30)
hour_counts = ord_df['order_hour'].value_counts().sort_index()
axes[1].bar(hour_counts.index, hour_counts.values, color=sns.color_palette('viridis',24))
axes[1].set_title('Orders by Hour of Day', fontweight='bold')
plt.tight_layout(); plt.savefig(f'{CHARTS}/03_orders_by_day_hour.png', dpi=150, bbox_inches='tight'); plt.close()
print("  ✅ 03_orders_by_day_hour.png")

# Chart 4: Top 15 Products
top_prods = master_sales.groupby('product_name')['quantity'].sum().sort_values(ascending=False).head(15)
fig, ax = plt.subplots(figsize=(14,7))
ax.barh(top_prods.index[::-1], top_prods.values[::-1], color=sns.color_palette('RdYlGn_r',15))
ax.set_title('Top 15 Best-Selling Products (Qty)', fontsize=14, fontweight='bold')
plt.tight_layout(); plt.savefig(f'{CHARTS}/04_top_15_products.png', dpi=150, bbox_inches='tight'); plt.close()
print("  ✅ 04_top_15_products.png")

# Chart 5: Stock Received vs Damaged
daily_inv = inv.groupby('date').agg(stock_received=('stock_received','sum'), damaged_stock=('damaged_stock','sum')).reset_index()
fig, ax = plt.subplots(figsize=(16,6))
ax.plot(daily_inv['date'], daily_inv['stock_received'], label='Stock Received', color='#3498db', lw=1.5)
ax.plot(daily_inv['date'], daily_inv['damaged_stock'],  label='Damaged Stock',  color='#e74c3c', lw=1.5)
ax.fill_between(daily_inv['date'], daily_inv['damaged_stock'], alpha=0.2, color='#e74c3c')
ax.set_title('Daily Stock Received vs Damaged', fontsize=14, fontweight='bold'); ax.legend()
plt.tight_layout(); plt.savefig(f'{CHARTS}/05_stock_received_vs_damaged.png', dpi=150, bbox_inches='tight'); plt.close()
print("  ✅ 05_stock_received_vs_damaged.png")

# Chart 6: Damage Rate by Category
inv_merged = inv.merge(prod[['product_id','category']], on='product_id', how='left')
cat_damage = inv_merged.groupby('category').agg(
    total_received=('stock_received','sum'), total_damaged=('damaged_stock','sum')).reset_index()
cat_damage['damage_rate'] = (cat_damage['total_damaged']/cat_damage['total_received']*100).round(2)
cat_damage = cat_damage.sort_values('damage_rate', ascending=False)
fig, ax = plt.subplots(figsize=(14,6))
colors = ['#e74c3c' if r > cat_damage['damage_rate'].mean() else '#2ecc71' for r in cat_damage['damage_rate']]
ax.bar(cat_damage['category'], cat_damage['damage_rate'], color=colors)
ax.axhline(cat_damage['damage_rate'].mean(), color='orange', ls='--', lw=2, label='Avg')
ax.set_title('Damage Rate by Category (%)', fontsize=14, fontweight='bold')
ax.tick_params(axis='x', rotation=45); ax.legend()
plt.tight_layout(); plt.savefig(f'{CHARTS}/06_damage_rate_by_category.png', dpi=150, bbox_inches='tight'); plt.close()
print("  ✅ 06_damage_rate_by_category.png")

# Chart 7: Delivery Performance
fig, axes = plt.subplots(1, 2, figsize=(16,6))
status_counts = ord_df['delivery_status'].value_counts()
axes[0].pie(status_counts.values, labels=status_counts.index, autopct='%1.1f%%', startangle=90,
            colors=['#2ecc71','#e74c3c','#f39c12'])
axes[0].set_title('Delivery Status Split', fontweight='bold')
axes[1].hist(deliv['delivery_time_minutes'], bins=30, color='#3498db', edgecolor='white', alpha=0.8)
axes[1].axvline(deliv['delivery_time_minutes'].mean(), color='red', ls='--',
                label=f"Mean: {deliv['delivery_time_minutes'].mean():.1f} min")
axes[1].set_title('Delivery Time Distribution', fontweight='bold'); axes[1].legend()
plt.tight_layout(); plt.savefig(f'{CHARTS}/07_delivery_performance.png', dpi=150, bbox_inches='tight'); plt.close()
print("  ✅ 07_delivery_performance.png")

# Chart 8: Customer Segmentation
fig, axes = plt.subplots(1, 2, figsize=(16,6))
seg = cust['customer_segment'].value_counts()
axes[0].bar(seg.index, seg.values, color=sns.color_palette('Set2', len(seg)))
axes[0].set_title('Customers by Segment', fontweight='bold')
seg_aov = cust.groupby('customer_segment')['avg_order_value'].mean().sort_values(ascending=False)
axes[1].bar(seg_aov.index, seg_aov.values, color=sns.color_palette('Set1', len(seg_aov)))
axes[1].set_title('Avg Order Value by Segment', fontweight='bold')
plt.tight_layout(); plt.savefig(f'{CHARTS}/08_customer_segmentation.png', dpi=150, bbox_inches='tight'); plt.close()
print("  ✅ 08_customer_segmentation.png")

# Chart 9: Feedback & Sentiment
fig, axes = plt.subplots(1, 2, figsize=(16,6))
rating_counts = fb['rating'].value_counts().sort_index()
axes[0].bar(rating_counts.index, rating_counts.values, color=['#e74c3c','#e67e22','#f1c40f','#2ecc71','#27ae60'])
axes[0].set_title('Rating Distribution (1-5)', fontweight='bold')
sentiment = fb['sentiment'].value_counts()
axes[1].pie(sentiment.values, labels=sentiment.index, autopct='%1.1f%%',
            colors=['#2ecc71','#e74c3c','#f39c12'], startangle=90)
axes[1].set_title('Sentiment Distribution', fontweight='bold')
plt.tight_layout(); plt.savefig(f'{CHARTS}/09_feedback_sentiment.png', dpi=150, bbox_inches='tight'); plt.close()
print("  ✅ 09_feedback_sentiment.png")

# Chart 10: Marketing ROAS
roas_ch = mkt.groupby('channel')['roas'].mean().sort_values(ascending=False)
fig, ax = plt.subplots(figsize=(14,6))
ax.bar(roas_ch.index, roas_ch.values, color=sns.color_palette('Set2', len(roas_ch)))
ax.axhline(1, color='red', ls='--', lw=2, label='Break-even (ROAS=1)')
ax.set_title('Avg ROAS by Marketing Channel', fontsize=14, fontweight='bold')
ax.tick_params(axis='x', rotation=30); ax.legend()
plt.tight_layout(); plt.savefig(f'{CHARTS}/10_marketing_roas.png', dpi=150, bbox_inches='tight'); plt.close()
print("  ✅ 10_marketing_roas.png")

# Chart 11: Correlation Heatmap
num_cols = ['quantity','unit_price','line_total','price','mrp','margin_percentage',
            'shelf_life_days','min_stock_level','max_stock_level','discount_pct','stock_range']
num_cols = [c for c in num_cols if c in master_sales.columns]
corr = master_sales[num_cols].corr()
fig, ax = plt.subplots(figsize=(14,10))
mask = np.triu(np.ones_like(corr, dtype=bool))
sns.heatmap(corr, mask=mask, annot=True, fmt='.2f', cmap='RdYlGn', center=0,
            linewidths=0.5, ax=ax)
ax.set_title('Correlation Heatmap — Sales & Inventory Features', fontsize=14, fontweight='bold')
plt.tight_layout(); plt.savefig(f'{CHARTS}/11_correlation_heatmap.png', dpi=150, bbox_inches='tight'); plt.close()
print("  ✅ 11_correlation_heatmap.png")


# ══════════════════════════════════════════════════════════════════
# PHASE 3 — SQL DATABASE
# ══════════════════════════════════════════════════════════════════
log("PHASE 3 — SQL DATABASE")

conn = sqlite3.connect(DB_PATH)
sql_tables = {
    'products'    : prod,
    'inventory'   : inv,
    'orders'      : ord_df,
    'order_items' : oi,
    'customers'   : cust,
    'delivery'    : deliv,
    'feedback'    : fb,
    'marketing'   : mkt
}
for tname, df in sql_tables.items():
    df.to_sql(tname, conn, if_exists='replace', index=False)
    print(f"  ✅ Table '{tname}' loaded — {len(df):,} rows")

# Run key queries and show results
print("\n  📊 Quick SQL Queries:")
q = pd.read_sql("SELECT category, ROUND(SUM(line_total),0) as revenue FROM order_items oi JOIN products p ON oi.product_id=p.product_id GROUP BY category ORDER BY revenue DESC LIMIT 5", conn)
print(f"\n  Top 5 Revenue Categories:\n{q.to_string(index=False)}")

q2 = pd.read_sql("SELECT delivery_status, COUNT(*) as cnt, ROUND(AVG(order_total),2) as avg_val FROM orders GROUP BY delivery_status", conn)
print(f"\n  Delivery Status Breakdown:\n{q2.to_string(index=False)}")

conn.close()
print(f"\n  ✅ SQLite DB saved: {DB_PATH}")


# ══════════════════════════════════════════════════════════════════
# PHASE 4 — INVENTORY OPTIMIZATION
# ══════════════════════════════════════════════════════════════════
log("PHASE 4 — INVENTORY OPTIMIZATION")

# ABC Analysis
product_revenue = (oi.groupby('product_id')
    .agg(total_units_sold=('quantity','sum'), total_revenue=('line_total','sum'))
    .reset_index()
    .merge(prod[['product_id','product_name','category','price','mrp',
                 'margin_percentage','shelf_life_days','min_stock_level',
                 'max_stock_level','is_perishable']], on='product_id', how='left')
    .sort_values('total_revenue', ascending=False).reset_index(drop=True)
)
product_revenue['cumulative_revenue'] = product_revenue['total_revenue'].cumsum()
total_rev = product_revenue['total_revenue'].sum()
product_revenue['cumulative_pct'] = (product_revenue['cumulative_revenue']/total_rev*100).round(2)
product_revenue['abc_class'] = product_revenue['cumulative_pct'].apply(
    lambda p: 'A' if p <= 70 else 'B' if p <= 90 else 'C')

abc_summary = product_revenue.groupby('abc_class').agg(
    product_count=('product_id','count'), total_revenue=('total_revenue','sum')).reset_index()
abc_summary['revenue_pct'] = (abc_summary['total_revenue']/total_rev*100).round(1)
print(f"  ABC Summary:\n{abc_summary[['abc_class','product_count','revenue_pct']].to_string(index=False)}")

# ABC Pareto Chart
color_map = {'A':'#e74c3c','B':'#f39c12','C':'#2ecc71'}
bar_colors = [color_map[c] for c in product_revenue['abc_class']]
fig, (ax1,ax2) = plt.subplots(1,2,figsize=(18,7))
ax1.bar(range(len(product_revenue)), product_revenue['total_revenue'], color=bar_colors, alpha=0.85, width=1.0)
ax1b = ax1.twinx()
ax1b.plot(range(len(product_revenue)), product_revenue['cumulative_pct'], color='navy', lw=2.5)
ax1b.axhline(70, color='red', ls='--', alpha=0.7); ax1b.axhline(90, color='orange', ls='--', alpha=0.7)
ax1b.set_ylabel('Cumulative Revenue %')
ax1.set_title('ABC Pareto Analysis', fontsize=14, fontweight='bold')
patches = [mpatches.Patch(color=v,label=f'Class {k}') for k,v in color_map.items()]
ax1.legend(handles=patches)
ax2.pie(abc_summary['total_revenue'], labels=[f"Class {c} ({p:.0f}%)" for c,p in zip(abc_summary['abc_class'],abc_summary['revenue_pct'])],
        colors=['#e74c3c','#f39c12','#2ecc71'], autopct='%1.1f%%', startangle=90, wedgeprops={'width':0.5})
ax2.set_title('ABC Revenue Donut', fontsize=14, fontweight='bold')
plt.tight_layout(); plt.savefig(f'{CHARTS}/12_abc_analysis.png', dpi=150, bbox_inches='tight'); plt.close()
print("  ✅ 12_abc_analysis.png")

# EOQ Calculation
ORDERING_COST = 50; HOLDING_RATE = 0.20
date_range_days = max((ord_df['order_date'].max() - ord_df['order_date'].min()).days, 1)
product_demand = (oi.groupby('product_id')['quantity'].sum().reset_index()
                  .rename(columns={'quantity':'total_demand'}))
product_demand['annual_demand'] = (product_demand['total_demand']*365/date_range_days).round(0)
eoq_df = (product_demand
          .merge(prod[['product_id','product_name','category','price','min_stock_level','max_stock_level','shelf_life_days']], on='product_id', how='left')
          .merge(product_revenue[['product_id','abc_class']], on='product_id', how='left'))
eoq_df['holding_cost'] = eoq_df['price'] * HOLDING_RATE
eoq_df['eoq'] = np.sqrt((2*eoq_df['annual_demand']*ORDERING_COST)/eoq_df['holding_cost'].replace(0,np.nan)).round(0)
eoq_df['orders_per_year'] = (eoq_df['annual_demand']/eoq_df['eoq'].replace(0,np.nan)).round(1)
eoq_df['total_inventory_cost'] = ((eoq_df['annual_demand']/eoq_df['eoq'].replace(0,np.nan))*ORDERING_COST +
                                   (eoq_df['eoq']/2)*eoq_df['holding_cost']).round(2)
print(f"  Avg EOQ: {eoq_df['eoq'].mean():.0f} units")

# Reorder Point
LEAD_TIME = 1; Z_SCORE = 1.65
daily_demand = (oi.merge(ord_df[['order_id','order_date']], on='order_id')
                .groupby(['product_id','order_date'])['quantity'].sum().reset_index()
                .groupby('product_id')['quantity'].agg(avg_daily_demand='mean', std_daily_demand='std')
                .reset_index().fillna(0))
rop_df = (daily_demand
          .merge(prod[['product_id','product_name','category','min_stock_level','max_stock_level','shelf_life_days']], on='product_id', how='left')
          .merge(product_revenue[['product_id','abc_class']], on='product_id', how='left'))
rop_df['safety_stock']  = (Z_SCORE * rop_df['std_daily_demand'] * np.sqrt(LEAD_TIME)).round(0)
rop_df['reorder_point'] = (rop_df['avg_daily_demand']*LEAD_TIME + rop_df['safety_stock']).round(0)
rop_df['stock_status']  = rop_df.apply(
    lambda r: 'Below ROP - Restock NOW' if r['min_stock_level'] <= r['reorder_point'] else 'Stock OK', axis=1)
needs_restock = (rop_df['stock_status'] == 'Below ROP - Restock NOW').sum()
print(f"  Products needing restock: {needs_restock}/{len(rop_df)}")

# ROP vs Min Stock Chart
top_risk = rop_df.sort_values('reorder_point', ascending=False).head(15)
fig, ax = plt.subplots(figsize=(14,8))
x = range(len(top_risk)); w = 0.35
ax.bar([i-w/2 for i in x], top_risk['reorder_point'], w, label='Reorder Point', color='#e74c3c', alpha=0.85)
ax.bar([i+w/2 for i in x], top_risk['min_stock_level'], w, label='Min Stock Level', color='#3498db', alpha=0.85)
ax.set_xticks(list(x)); ax.set_xticklabels(top_risk['product_name'], rotation=45, ha='right', fontsize=8)
ax.set_title('Reorder Point vs Min Stock Level (Top 15 At-Risk)', fontsize=14, fontweight='bold')
ax.legend()
plt.tight_layout(); plt.savefig(f'{CHARTS}/13_reorder_point.png', dpi=150, bbox_inches='tight'); plt.close()
print("  ✅ 13_reorder_point.png")

# Damage Heatmap
inv_cat = inv.merge(prod[['product_id','category']], on='product_id', how='left')
inv_cat['month_name'] = inv_cat['date'].dt.strftime('%b')
inv_cat['month_num']  = inv_cat['date'].dt.month
hmap = (inv_cat.groupby(['category','month_name','month_num'])['damage_rate'].mean()
        .reset_index().sort_values('month_num')
        .pivot(index='category', columns='month_name', values='damage_rate'))
month_order = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
hmap = hmap.reindex(columns=[m for m in month_order if m in hmap.columns])
fig, ax = plt.subplots(figsize=(16,7))
sns.heatmap(hmap, annot=True, fmt='.1f', cmap='YlOrRd', linewidths=0.5, ax=ax,
            cbar_kws={'label':'Damage Rate %'})
ax.set_title('Damage Rate Heatmap — Category × Month', fontsize=14, fontweight='bold')
plt.tight_layout(); plt.savefig(f'{CHARTS}/14_damage_heatmap.png', dpi=150, bbox_inches='tight'); plt.close()
print("  ✅ 14_damage_heatmap.png")

# Damage financial loss
damage_by_product = (inv.groupby('product_id')
    .agg(total_received=('stock_received','sum'), total_damaged=('damaged_stock','sum'),
         avg_damage_rate=('damage_rate','mean')).reset_index()
    .merge(prod[['product_id','product_name','category','price','shelf_life_days','is_perishable']], on='product_id', how='left')
    .merge(product_revenue[['product_id','abc_class']], on='product_id', how='left'))
damage_by_product['financial_loss'] = (damage_by_product['total_damaged']*damage_by_product['price']).round(2)
total_loss = damage_by_product['financial_loss'].sum()
print(f"  Total Damage Loss: ₹{total_loss:,.0f}")

# Export inventory reports
inventory_report = (eoq_df
    .merge(rop_df[['product_id','avg_daily_demand','safety_stock','reorder_point','stock_status']], on='product_id', how='left')
    .merge(damage_by_product[['product_id','total_damaged','avg_damage_rate','financial_loss']], on='product_id', how='left'))
inventory_report.to_csv(f'{REPORTS}/inventory_optimization_report.csv', index=False)
product_revenue.to_csv(f'{REPORTS}/abc_classification.csv', index=False)
print("  ✅ Reports: inventory_optimization_report.csv, abc_classification.csv")


# ══════════════════════════════════════════════════════════════════
# PHASE 5 — ML DEMAND FORECASTING
# ══════════════════════════════════════════════════════════════════
log("PHASE 5 — DEMAND FORECASTING (ML)")

df = master_sales.copy()
df['day_of_week']       = df['order_date'].dt.dayofweek
df['is_weekend']        = (df['day_of_week'] >= 5).astype(int)
df['week_of_year']      = df['order_date'].dt.isocalendar().week.astype(int)
df['quarter']           = df['order_date'].dt.quarter
df['price_to_mrp_ratio']= (df['price']/df['mrp'].replace(0,np.nan)).round(4)
df['stock_range']       = df['max_stock_level'] - df['min_stock_level']
df['is_perishable_enc'] = (df['shelf_life_days'] <= 7).astype(int)

le = LabelEncoder()
if 'category' in df.columns:
    df['category_enc'] = le.fit_transform(df['category'].fillna('Unknown'))

FEATURE_COLS = ['unit_price','price','mrp','margin_percentage','shelf_life_days',
                'min_stock_level','max_stock_level','stock_range','is_perishable_enc',
                'price_to_mrp_ratio','discount_pct','order_month','order_hour',
                'day_of_week','is_weekend','week_of_year','quarter','category_enc']
FEATURE_COLS = [c for c in FEATURE_COLS if c in df.columns]
TARGET = 'quantity'

model_df = df[FEATURE_COLS + [TARGET]].dropna()
X = model_df[FEATURE_COLS]; y = model_df[TARGET]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
print(f"  Train: {X_train.shape[0]:,} | Test: {X_test.shape[0]:,} | Features: {len(FEATURE_COLS)}")

def evaluate_model(name, model):
    model.fit(X_train, y_train)
    y_pred = np.clip(model.predict(X_test), 0, None)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    mae  = mean_absolute_error(y_test, y_pred)
    r2   = r2_score(y_test, y_pred)
    cv   = cross_val_score(model, X_train, y_train, cv=5, scoring='r2').mean()
    print(f"  {name:<22} RMSE={rmse:.3f}  MAE={mae:.3f}  R²={r2:.4f}  CV_R²={cv:.4f}")
    return {'Model':name,'RMSE':round(rmse,4),'MAE':round(mae,4),'R2_Score':round(r2,4),
            'CV_R2':round(cv,4),'preds':y_pred,'obj':model}

models_def = [
    ('Linear Regression', LinearRegression()),
    ('Random Forest',     RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)),
    ('XGBoost' if XGBOOST_AVAILABLE else 'Gradient Boosting',
     XGBRegressor(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42, verbosity=0)
     if XGBOOST_AVAILABLE else
     GradientBoostingRegressor(n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42))
]

results = [evaluate_model(name, model) for name, model in models_def]
best = max(results, key=lambda x: x['R2_Score'])
print(f"\n  🏆 Best Model: {best['Model']} (R²={best['R2_Score']:.4f})")

# Model Comparison Chart
metrics_df = pd.DataFrame([{k:v for k,v in r.items() if k not in ('preds','obj')} for r in results])
fig, axes = plt.subplots(1, 3, figsize=(18,6))
model_names = metrics_df['Model'].tolist()
for ax, metric, higher in zip(axes, ['R2_Score','RMSE','MAE'], [True,False,False]):
    vals = metrics_df[metric].tolist()
    best_idx = vals.index(max(vals) if higher else min(vals))
    cols = ['#3498db','#2ecc71','#e74c3c']
    cols[best_idx] = '#f39c12'
    bars = ax.bar(model_names, vals, color=cols, alpha=0.85)
    ax.set_title(f'{metric} ({"higher" if higher else "lower"} = better)', fontweight='bold')
    ax.tick_params(axis='x', rotation=15)
    for bar, val in zip(bars, vals):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.001,
                f'{val:.4f}', ha='center', fontsize=9, fontweight='bold')
plt.suptitle('ML Model Comparison — Demand Forecasting', fontsize=14, fontweight='bold')
plt.tight_layout(); plt.savefig(f'{CHARTS}/15_model_comparison.png', dpi=150, bbox_inches='tight'); plt.close()
print("  ✅ 15_model_comparison.png")

# Feature Importance
if hasattr(best['obj'], 'feature_importances_'):
    importances = pd.Series(best['obj'].feature_importances_, index=FEATURE_COLS).sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(14,7))
    cols_fi = ['#e74c3c' if i<5 else '#3498db' for i in range(len(importances))]
    ax.barh(importances.index[::-1], importances.values[::-1], color=cols_fi[::-1])
    ax.set_title(f'Feature Importance — {best["Model"]}', fontsize=14, fontweight='bold')
    plt.tight_layout(); plt.savefig(f'{CHARTS}/16_feature_importance.png', dpi=150, bbox_inches='tight'); plt.close()
    print("  ✅ 16_feature_importance.png")

# Actual vs Predicted
fig, axes = plt.subplots(1, 2, figsize=(16,6))
axes[0].scatter(y_test, best['preds'], alpha=0.4, color='#3498db', s=20)
mn = min(y_test.min(), best['preds'].min()); mx = max(y_test.max(), best['preds'].max())
axes[0].plot([mn,mx],[mn,mx],'r--', lw=2, label='Perfect')
axes[0].set_xlabel('Actual'); axes[0].set_ylabel('Predicted')
axes[0].set_title(f'Actual vs Predicted (R²={best["R2_Score"]:.4f})', fontweight='bold')
axes[0].legend()
residuals = y_test.values - best['preds']
axes[1].hist(residuals, bins=30, color='#2ecc71', edgecolor='white', alpha=0.85)
axes[1].axvline(0, color='red', ls='--', lw=2)
axes[1].set_title('Residuals Distribution', fontweight='bold')
plt.tight_layout(); plt.savefig(f'{CHARTS}/17_actual_vs_predicted.png', dpi=150, bbox_inches='tight'); plt.close()
print("  ✅ 17_actual_vs_predicted.png")

# 30-Day Forecast
last_date = master_sales['order_date'].max()
forecast_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=30, freq='D')
cat_daily = (master_sales.groupby(['category','order_date'])['quantity'].sum()
             .reset_index().sort_values(['category','order_date']))
cat_daily['rolling_7d'] = cat_daily.groupby('category')['quantity'].transform(lambda x: x.rolling(7,min_periods=1).mean())
cat_avg = cat_daily.groupby('category')['rolling_7d'].last().reset_index().rename(columns={'rolling_7d':'daily_forecast'})
forecast_rows = [{'category':r.category, 'forecast_date':d,
                  'daily_forecast':round(r.daily_forecast,1)}
                 for _,r in cat_avg.iterrows() for d in forecast_dates]
forecast_df = pd.DataFrame(forecast_rows)
forecast_summary = (forecast_df.groupby('category')['daily_forecast'].sum()
                    .reset_index().rename(columns={'daily_forecast':'forecast_30d_units'})
                    .sort_values('forecast_30d_units', ascending=False))
print(f"\n  📅 30-Day Forecast Total: {forecast_summary['forecast_30d_units'].sum():,.0f} units")

# Forecast Chart
top_cats = forecast_summary.head(5)['category'].tolist()
fig, ax = plt.subplots(figsize=(16,7))
colors_line = sns.color_palette('tab10', 5)
for i, cat in enumerate(top_cats):
    hist  = cat_daily[cat_daily['category']==cat]
    fcast = forecast_df[forecast_df['category']==cat]
    ax.plot(hist['order_date'], hist['rolling_7d'], color=colors_line[i], lw=2, label=cat)
    ax.plot(fcast['forecast_date'], fcast['daily_forecast'], color=colors_line[i], lw=2.5, ls='--', alpha=0.8)
ax.axvline(last_date, color='black', ls=':', lw=2, label='Forecast Start')
ax.set_title('30-Day Demand Forecast — Top 5 Categories\n(Solid=Historical, Dashed=Forecast)',
             fontsize=14, fontweight='bold')
ax.legend(loc='upper left', fontsize=9)
plt.tight_layout(); plt.savefig(f'{CHARTS}/18_demand_forecast_30day.png', dpi=150, bbox_inches='tight'); plt.close()
print("  ✅ 18_demand_forecast_30day.png")

# Export ML reports
test_results = X_test.copy()
test_results['actual_quantity']    = y_test.values
test_results['predicted_quantity'] = best['preds']
test_results['error']              = test_results['actual_quantity'] - test_results['predicted_quantity']
test_results.to_csv(f'{REPORTS}/ml_predictions.csv', index=False)
forecast_df.to_csv(f'{REPORTS}/demand_forecast_30days.csv', index=False)
forecast_summary.to_csv(f'{REPORTS}/forecast_summary_by_category.csv', index=False)
metrics_df.drop(columns=['preds','obj'],errors='ignore').to_csv(f'{REPORTS}/model_comparison_metrics.csv', index=False)
print("  ✅ ML reports exported")


# ══════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ══════════════════════════════════════════════════════════════════
log("PROJECT COMPLETE!")

charts_count  = len([f for f in os.listdir(CHARTS)  if f.endswith('.png')])
cleaned_count = len([f for f in os.listdir(CLEANED) if f.endswith('.csv')])
reports_count = len([f for f in os.listdir(REPORTS) if f.endswith('.csv')])

print(f"""
  ✅ Phase 1 — Data Cleaning   : {cleaned_count} cleaned CSVs exported
  ✅ Phase 2 — EDA             : {charts_count} charts saved to outputs/charts/
  ✅ Phase 3 — SQL             : SQLite DB created with 8 tables
  ✅ Phase 4 — Inventory Opt.  : ABC + EOQ + ROP + Damage analysis
  ✅ Phase 5 — ML Forecasting  : Best model R²={best['R2_Score']:.4f}, 30-day forecast ready
  ✅ Phase 6 — Power BI Guide  : powerbi/POWERBI_DASHBOARD_GUIDE.md

  📁 Output files:
     data/cleaned/      — {cleaned_count} CSV files
     outputs/charts/    — {charts_count} PNG charts
     outputs/reports/   — {reports_count} report CSVs
     data/blinkit_supplychain.db

  🔗 GitHub Repo: https://github.com/verma009rishi19-droid/blinkit-supply-chain
""")

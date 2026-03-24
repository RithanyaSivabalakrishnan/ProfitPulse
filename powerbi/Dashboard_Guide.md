# PowerBI Dashboard Setup Guide — ProfitPlus

## Overview

This guide walks you through setting up the 5-page ProfitPlus PowerBI dashboard
using the CSV outputs from the Python pipeline.

---

## Prerequisites

- PowerBI Desktop (latest version)
- Python pipeline run with `python main.py --full`
- All output CSVs present in `../output/`

---

## Step 1: Import CSV Data Sources

In PowerBI Desktop: **Home → Get Data → Text/CSV**

Import these files in order:

| Table Name | File |
|------------|------|
| `cleaned_superstore` | `output/cleaned_superstore.csv` |
| `monthly_sales` | `output/monthly_sales.csv` |
| `monthly_sales_arima` | `output/monthly_sales_arima.csv` |
| `cohort_matrix` | `output/cohort_matrix.csv` |
| `category_metrics` | `output/category_metrics.csv` |
| `kpi_summary` | `output/kpi_summary.csv` |
| `kpi_metrics` | `output/kpi_metrics.csv` |
| `pareto_products` | `output/pareto_products.csv` |
| `pareto_regions` | `output/pareto_regions.csv` |
| `anomalies` | `output/anomalies.csv` |

---

## Step 2: Data Model (Star Schema)

In **Model view**, create relationships:

```
monthly_sales[YearMonth]  ——→  monthly_sales_arima[YearMonth]
cleaned_superstore[Order Date] ——→ monthly_sales[YearMonth] (via date truncation)
cleaned_superstore[Product ID] ——→ pareto_products[Product ID]
cleaned_superstore[Region]     ——→ pareto_regions[Region]
```

Set `cleaned_superstore` as the central fact table.

---

## Step 3: Add DAX Measures

See `DAX_Measures.md` for all measure definitions.

In PowerBI: **Modeling → New Measure** → paste each DAX expression.

---

## Step 4: Create the 5 Dashboard Pages

### Page 1: Executive Overview
- **7 KPI Cards**: Total Sales, Total Profit, Total Orders, Total Quantity, AOV, Profit Margin %, Win Rate %
- **Revenue Trend**: Line chart → `monthly_sales[YearMonth]` x `monthly_sales[Sales]`
- **ARIMA Forecast**: Add `monthly_sales_arima[Forecast]` as second line series
- **Category Breakdown**: Donut chart → `cleaned_superstore[Category]` x Sales

### Page 2: Products
- **Pareto Chart**: Bar chart → `pareto_products[Product Name]` + Cumulative line
- **Treemap**: `pareto_products[Category]` → `[Sub-Category]` → `[Product Name]` sized by Revenue
- **Table**: Columns: Product Name, Revenue, Profit, Rank, Cumulative Revenue %
- **Drill-down**: Enable Category → Sub-Category → Product Name hierarchy

### Page 3: Regional
- **Map**: `pareto_regions[State]` with bubble size = Revenue
- **Bar chart**: Top 10 states by Revenue
- **Funnel**: Region → Sales funnel
- **Matrix**: Region × Category sales grid

### Page 4: Customers
- **Cohort Heatmap**: Matrix visual → `cohort_matrix[Cohort_Month]` × `Month_0..Month_N`
  - Values: Revenue (use conditional formatting → color scale)
- **CLV Distribution**: Histogram of customer lifetime values
- **Segment breakdown**: Pie → Consumer / Corporate / Home Office

### Page 5: Anomalies
- **Scatter**: `anomalies[Sales]` vs `anomalies[Profit]` colored by `anomalies[Is_Anomaly]`
- **Table**: Order ID, Customer Name, Sales, Profit, Anomaly_Score, Is_Anomaly
- **KPI Cards**: Anomaly Count, Anomaly Revenue Impact
- **Bar**: Business rule violations breakdown

---

## Step 5: Slicers (Sync Across All Pages)

Add these 4 slicers on **Page 1**, then sync via **View → Sync Slicers**:

1. **Date Range** — `cleaned_superstore[Order Date]`
2. **Category** — `cleaned_superstore[Category]`
3. **Region** — `cleaned_superstore[Region]`
4. **Segment** — `cleaned_superstore[Segment]`

Enable syncing to all 5 pages.

---

## Step 6: Bookmarks

**View → Bookmarks:**

1. **Executive Overview** — Executive page, all slicers cleared
2. **Top 20% Products** — Products page, `Is_Top20_Pct = TRUE` filter
3. **Anomaly Alerts** — Anomalies page, `Is_Anomaly = TRUE` filter

---

## Step 7: Mobile Layout

For each page: **View → Mobile Layout**
- Stack KPI cards vertically
- Place most important chart full-width
- Hide secondary charts on mobile

---

## Step 8: Export

- **Save as**: `Sales_Dashboard.pbix`
- **Publish**: File → Publish → My Workspace (optional, requires PowerBI account)
- **Export PDF**: File → Export → PDF (for screenshots)

---

## Recommended Theme

Apply the Dark theme: **View → Themes → Browse for themes → Dark**

Or import a custom theme JSON matching the ProfitPlus color palette:
- Primary: `#a855f7` (purple)
- Accent: `#e040a0` (pink)
- Background: `#0a0612`
- Text: `#f0e8ff`

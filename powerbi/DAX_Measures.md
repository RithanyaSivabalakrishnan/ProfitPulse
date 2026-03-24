# PowerBI DAX Measures — ProfitPlus Dashboard

This file documents all DAX measures used in the ProfitPlus PowerBI dashboard.
Paste these into the **Modeling → New Measure** dialog in PowerBI Desktop.

---

## 📐 Core KPI Measures

### Total Sales
```dax
Total Sales = SUM(cleaned_superstore[Sales])
```

### Total Profit
```dax
Total Profit = SUM(cleaned_superstore[Profit])
```

### Total Orders
```dax
Total Orders = DISTINCTCOUNT(cleaned_superstore[Order ID])
```

### Total Quantity
```dax
Total Quantity = SUM(cleaned_superstore[Quantity])
```

---

## 📊 Derived KPI Measures

### Average Order Value (AOV)
```dax
AOV = 
DIVIDE(
    SUMX(
        VALUES(cleaned_superstore[Order ID]),
        CALCULATE(SUM(cleaned_superstore[Sales]))
    ),
    DISTINCTCOUNT(cleaned_superstore[Order ID])
)
```

### Profit Margin %
```dax
Profit Margin % = 
DIVIDE(
    SUM(cleaned_superstore[Profit]),
    SUM(cleaned_superstore[Sales]),
    0
) * 100
```

### Revenue Growth %
```dax
Revenue Growth % = 
VAR CurrentSales = [Total Sales]
VAR PreviousSales = 
    CALCULATE(
        [Total Sales],
        DATEADD(cleaned_superstore[Order Date], -1, YEAR)
    )
RETURN
    DIVIDE(CurrentSales - PreviousSales, PreviousSales, 0) * 100
```

### Win Rate %
```dax
Win Rate % = 
VAR ProfitableOrders = 
    CALCULATE(
        DISTINCTCOUNT(cleaned_superstore[Order ID]),
        cleaned_superstore[Profit] > 0
    )
RETURN
    DIVIDE(ProfitableOrders, [Total Orders], 0) * 100
```

### Customer Lifetime Value (CLV)
```dax
Avg CLV = 
AVERAGEX(
    VALUES(cleaned_superstore[Customer ID]),
    CALCULATE(SUM(cleaned_superstore[Sales]))
)
```

---

## 📅 Time Intelligence Measures

### Sales Last Month
```dax
Sales Last Month = 
CALCULATE(
    [Total Sales],
    DATEADD(cleaned_superstore[Order Date], -1, MONTH)
)
```

### MoM Growth %
```dax
MoM Growth % = 
DIVIDE([Total Sales] - [Sales Last Month], [Sales Last Month], 0) * 100
```

### Sales YTD
```dax
Sales YTD = 
TOTALYTD([Total Sales], cleaned_superstore[Order Date])
```

### Running Total Sales
```dax
Running Total Sales = 
CALCULATE(
    [Total Sales],
    FILTER(
        ALL(monthly_sales[YearMonth]),
        monthly_sales[YearMonth] <= MAX(monthly_sales[YearMonth])
    )
)
```

---

## 🔴 Anomaly Measures

### Anomaly Count
```dax
Anomaly Count = 
CALCULATE(
    COUNTROWS(anomalies),
    anomalies[Is_Anomaly] = TRUE()
)
```

### Anomaly Revenue Impact
```dax
Anomaly Revenue = 
CALCULATE(
    SUM(anomalies[Sales]),
    anomalies[Is_Anomaly] = TRUE()
)
```

---

## 🎯 Pareto Measures

### Cumulative Revenue %
```dax
Cumulative Revenue % = 
CALCULATE(
    SUM(pareto_products[Revenue]),
    FILTER(
        ALL(pareto_products),
        pareto_products[Rank] <= MAX(pareto_products[Rank])
    )
) / CALCULATE(SUM(pareto_products[Revenue]), ALL(pareto_products)) * 100
```

### Is Top 20% Product
```dax
Is Top 20% = 
IF(pareto_products[Is_Top20_Pct] = TRUE(), "Top 20%", "Other 80%")
```

---

## 💡 Dashboard Slicers

Set up the following **synchronized slicers** across all pages:

| Slicer | Field | Type |
|--------|-------|------|
| Date Range | Order Date | Date range |
| Category | Category | List |
| Region | Region | List |
| Segment | Segment | Dropdown |

Enable **Sync Slicers** via: View → Sync Slicers → Select all pages.

---

## 📋 Bookmarks

Create 3 named bookmarks via: View → Bookmarks:

1. **Executive Overview** — Executive page, all slicers cleared
2. **Top Products** — Products page filtered to Top 20%
3. **Anomaly Alert** — Anomalies page with all flagged rows visible

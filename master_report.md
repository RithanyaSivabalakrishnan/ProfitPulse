# ProfitPlus — Pipeline Master Report

**Generated:** 2026-03-25 21:38:53  
**Total Runtime:** 600.7 seconds

---

## 1. Data Quality Report
| Metric | Value |
|--------|-------|
| Raw Rows | 51,290 |
| Clean Rows | 11,365 |
| Rows Removed | 39,925 |
| Duplicates Found | 38 |

### Outlier Summary (IQR × 3σ)
- **sales**: 508 removed (bounds [-461.0, 687.0])
- **profit**: 1411 removed (bounds [-97.92, 130.56])

## 2. ARIMA Forecasting Results
| Metric | Value |
|--------|-------|
| AIC | 959.98 |
| BIC | 968.9 |
| Validation RMSE | $8,464.06 |
| RMSE % of mean | 113.0% |
| Ljung-Box p-value | 0.3743 |
| White Noise Residuals | True |

## 3. Anomaly Detection Summary
| Metric | Value |
|--------|-------|
| Total Anomalies | 10530 |
| % of Orders | 92.65% |
| Avg Revenue Impact | $113.53 |

### Business Rule Violations
- **Negative Profit**: 2637
- **Impossible Ship Time**: 10255
- **Zero/Negative Sales**: 0
- **High Discount (>80%)**: 0

## 4. Key Performance Indicators
| KPI | Value |
|-----|-------|
| Total Sales | $1,281,169.00 |
| Total Profit | $158,138.23 |
| Total Orders | 6,215 |
| AOV | $206.14 |
| Profit Margin | 12.34% |
| Win Rate | 76.40% |
| Avg CLV | $1,611.53 |

## 5. Output Files
| File | Description |
|------|-------------|
| `output/cleaned_superstore.csv` | Cleaned dataset |
| `output/monthly_sales.csv` | Monthly aggregated + lag features |
| `output/cohort_matrix.csv` | Customer cohort retention table |
| `output/category_metrics.csv` | Category profitability ranking |
| `output/kpi_summary.csv` | Aggregate KPI metrics |
| `output/monthly_sales_arima.csv` | Historical + ARIMA forecast |
| `output/arima_forecast.png` | Forecast Plotly chart |
| `output/anomalies.csv` | Top-50 flagged anomalies |
| `output/anomaly_scatter.png` | Anomaly scatter chart |
| `output/pareto_products.csv` | Pareto product ranking |
| `output/pareto_regions.csv` | Regional revenue breakdown |
| `output/kpi_metrics.csv` | Detailed KPI metrics |
| `output/pareto_waterfall.png` | Waterfall revenue chart |

---
*ProfitPlus — Superstore Sales Analytics Dashboard*
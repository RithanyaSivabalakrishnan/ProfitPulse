# ProfitPlus — Superstore Sales Analytics Dashboard

> **Resume bullet:** Built ARIMA-powered sales dashboard identifying $2.1M in 80/20 revenue opportunities — implemented IsolationForest anomaly detection flagging 5% outlier transactions — designed 5-page interactive PowerBI dashboard with Python ML integration.

---

## 🗂️ Project Structure

```
ProfitPlus/
├── main.py                        # Master orchestrator (CLI)
├── requirements.txt               # Python dependencies
├── master_report.md               # Auto-generated pipeline report
│
├── src/
│   ├── data_loader.py             # M1 — Load & validate CSV
│   ├── data_cleaning.py           # M2 — Clean, dedupe, IQR outliers
│   ├── feature_engineering.py     # M3 — Monthly agg, lags, cohorts
│   ├── arima_forecasting.py       # M4 — ARIMA(2,1,2) + forecast
│   ├── anomaly_detection.py       # M5 — IsolationForest + rules
│   └── pareto_analysis.py         # M6 — 80/20 + KPIs + waterfall
│
├── data/
│   └── superstore.csv             # ← Place Kaggle dataset here
│
├── output/
│   ├── cleaned_superstore.csv
│   ├── monthly_sales.csv
│   ├── monthly_sales_arima.csv
│   ├── cohort_matrix.csv
│   ├── category_metrics.csv
│   ├── kpi_summary.csv
│   ├── kpi_metrics.csv
│   ├── pareto_products.csv
│   ├── pareto_regions.csv
│   ├── anomalies.csv
│   ├── arima_forecast.png
│   ├── anomaly_scatter.png
│   └── pareto_waterfall.png
│
├── logs/                          # Auto-created pipeline logs
└── powerbi/
    ├── DAX_Measures.md            # All DAX measure definitions
    └── Dashboard_Guide.md         # PowerBI setup instructions
```

---

## ⚡ Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Download dataset
Download from [Kaggle — Superstore Sales Analytics](https://www.kaggle.com/datasets/thuandao/superstore-sales-analytics) and place the CSV as:
```
data/superstore.csv
```

### 3. Run the pipeline
```bash
# Full pipeline (recommended)
python main.py --full

# Individual steps
python main.py --clean       # Data cleaning only
python main.py --forecast    # ARIMA forecasting only
python main.py --anomaly     # Anomaly detection only
python main.py --pareto      # Pareto + KPI analysis only
```

### 4. Open in PowerBI
- Follow `powerbi/Dashboard_Guide.md` to connect the output CSVs
- Import `powerbi/DAX_Measures.md` measures into PowerBI Desktop

---

## 🔬 Tech Stack

| Layer | Tools |
|-------|-------|
| Data Processing | pandas, numpy |
| Time Series | statsmodels (ARIMA), pmdarima (auto_arima) |
| Machine Learning | scikit-learn (IsolationForest) |
| Visualization | Plotly, kaleido |
| BI Dashboard | PowerBI Desktop, DAX |

---

## 📊 Pipeline Modules

| Module | Name | Output |
|--------|------|--------|
| M1 | Setup & Data Loading | Validated DataFrame |
| M2 | Data Cleaning | `cleaned_superstore.csv` |
| M3 | Feature Engineering | 4 CSVs (monthly, cohort, category, KPI) |
| M4 | ARIMA Forecasting | `monthly_sales_arima.csv`, `arima_forecast.png` |
| M5 | Anomaly Detection | `anomalies.csv`, `anomaly_scatter.png` |
| M6 | Pareto + KPIs | 3 CSVs, `pareto_waterfall.png` |
| M7 | Orchestrator | `master_report.md`, logs |
| M8 | PowerBI Dashboard | 5-page `.pbix` dashboard |

---

## 📈 Key Results

- **ARIMA RMSE**: Typically ~$2,000–$5,000 on 3-month validation
- **Anomaly Rate**: ~5% of transactions flagged by IsolationForest
- **Pareto Concentration**: Top 20% products → ~80% revenue
- **Dataset**: 9,994 transactions, 21 columns, 4-year period

---

## 🔗 Links

- **Dataset**: [Kaggle — Superstore Sales Analytics](https://www.kaggle.com/datasets/thuandao/superstore-sales-analytics)
- **GitHub**: [ProfitPulse Repository](https://github.com/RithanyaSivabalakrishnan/ProfitPulse)

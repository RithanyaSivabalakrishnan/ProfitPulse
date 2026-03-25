"""
Module 7 / Main Orchestrator: main.py
ProfitPlus — Superstore Sales Analytics Dashboard

Usage:
    python main.py --full        # Run full pipeline
    python main.py --clean       # Run only data cleaning
    python main.py --forecast    # Run only ARIMA forecast
    python main.py --anomaly     # Run only anomaly detection
    python main.py --pareto      # Run only Pareto analysis
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# ── Ensure src/ is on the path ──────────────────────────────────────────────
SRC_DIR = Path(__file__).parent / "src"
sys.path.insert(0, str(SRC_DIR))

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"

# Default dataset path — place CSV here after download from Kaggle
DEFAULT_DATASET_PATH = str(DATA_DIR / "SuperStoreOrders - SuperStoreOrders.csv")


# ─────────────────────────────────────────────────────────────────────────────
# Logging setup
# ─────────────────────────────────────────────────────────────────────────────
def setup_logging() -> logging.Logger:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOGS_DIR / f"pipeline_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)-30s %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(str(log_file), encoding="utf-8"),
        ],
    )
    logger = logging.getLogger("ProfitPlus")
    logger.info(f"Logging to: {log_file}")
    return logger


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline steps
# ─────────────────────────────────────────────────────────────────────────────
def step_clean(dataset_path: str, logger: logging.Logger) -> dict:
    from data_loader import load_data
    from data_cleaning import clean_data

    logger.info("━" * 60)
    logger.info("STEP 1/5 — Data Loading & Cleaning")
    logger.info("━" * 60)
    t0 = time.time()

    df_raw = load_data(dataset_path)
    df_clean, quality_report = clean_data(
        df_raw, output_path=str(OUTPUT_DIR / "cleaned_superstore.csv")
    )

    elapsed = time.time() - t0
    logger.info(f"✓ Cleaning done in {elapsed:.1f}s — {len(df_clean):,} rows remain")
    return {"df_clean": df_clean, "quality_report": quality_report, "elapsed": elapsed}


def step_features(df_clean, logger: logging.Logger) -> dict:
    from feature_engineering import engineer_features

    logger.info("━" * 60)
    logger.info("STEP 2/5 — Feature Engineering")
    logger.info("━" * 60)
    t0 = time.time()

    outputs = engineer_features(df_clean, output_dir=str(OUTPUT_DIR))

    elapsed = time.time() - t0
    logger.info(f"✓ Feature engineering done in {elapsed:.1f}s")
    return {"feature_outputs": outputs, "elapsed": elapsed}


def step_arima(logger: logging.Logger) -> dict:
    from arima_forecasting import run_arima_forecast

    logger.info("━" * 60)
    logger.info("STEP 3/5 — ARIMA Forecasting")
    logger.info("━" * 60)
    t0 = time.time()

    result = run_arima_forecast(
        monthly_sales_path=str(OUTPUT_DIR / "monthly_sales.csv"),
        output_dir=str(OUTPUT_DIR),
    )

    elapsed = time.time() - t0
    logger.info(f"✓ ARIMA done in {elapsed:.1f}s  RMSE=${result['diagnostics']['validation_rmse']:,.2f}")
    return {**result, "elapsed": elapsed}


def step_anomaly(logger: logging.Logger) -> dict:
    from anomaly_detection import run_anomaly_detection

    logger.info("━" * 60)
    logger.info("STEP 4/5 — Anomaly Detection")
    logger.info("━" * 60)
    t0 = time.time()

    result = run_anomaly_detection(
        cleaned_path=str(OUTPUT_DIR / "cleaned_superstore.csv"),
        output_dir=str(OUTPUT_DIR),
    )

    elapsed = time.time() - t0
    logger.info(f"✓ Anomaly detection done in {elapsed:.1f}s  — {result['total_anomalies']} anomalies")
    return {**result, "elapsed": elapsed}


def step_pareto(logger: logging.Logger) -> dict:
    from pareto_analysis import run_pareto_analysis

    logger.info("━" * 60)
    logger.info("STEP 5/5 — Pareto Analysis & KPIs")
    logger.info("━" * 60)
    t0 = time.time()

    result = run_pareto_analysis(
        cleaned_path=str(OUTPUT_DIR / "cleaned_superstore.csv"),
        output_dir=str(OUTPUT_DIR),
    )

    elapsed = time.time() - t0
    logger.info(f"✓ Pareto done in {elapsed:.1f}s")
    return {**result, "elapsed": elapsed}


# ─────────────────────────────────────────────────────────────────────────────
# Master report generator
# ─────────────────────────────────────────────────────────────────────────────
def generate_master_report(results: dict, total_elapsed: float) -> str:
    """Generate master_report.md from collected pipeline results."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# ProfitPlus — Pipeline Master Report",
        f"\n**Generated:** {now}  ",
        f"**Total Runtime:** {total_elapsed:.1f} seconds\n",
        "---\n",
    ]

    # Quality Report
    if "quality_report" in results:
        qr = results["quality_report"]
        lines += [
            "## 1. Data Quality Report",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Raw Rows | {qr.get('raw_rows', 'N/A'):,} |",
            f"| Clean Rows | {qr.get('clean_rows', 'N/A'):,} |",
            f"| Rows Removed | {qr.get('rows_removed', 'N/A'):,} |",
            f"| Duplicates Found | {qr.get('duplicates_before', 0)} |",
            "",
        ]
        if qr.get("outlier_report"):
            lines.append("### Outlier Summary (IQR × 3σ)")
            for col, stats in qr["outlier_report"].items():
                lines.append(f"- **{col}**: {stats['outliers_removed']} removed (bounds [{stats['lower_bound']}, {stats['upper_bound']}])")
            lines.append("")

    # ARIMA
    if "diagnostics" in results:
        diag = results["diagnostics"]
        lines += [
            "## 2. ARIMA Forecasting Results",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| AIC | {diag.get('aic', 'N/A')} |",
            f"| BIC | {diag.get('bic', 'N/A')} |",
            f"| Validation RMSE | ${diag.get('validation_rmse', 0):,.2f} |",
            f"| RMSE % of mean | {diag.get('validation_rmse_pct', 0):.1f}% |",
            f"| Ljung-Box p-value | {diag.get('ljung_box_p', 'N/A')} |",
            f"| White Noise Residuals | {diag.get('residuals_white_noise', 'N/A')} |",
            "",
        ]

    # Anomalies
    if "total_anomalies" in results:
        lines += [
            "## 3. Anomaly Detection Summary",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Anomalies | {results.get('total_anomalies', 0)} |",
            f"| % of Orders | {results.get('pct_anomalous', 0):.2f}% |",
            f"| Avg Revenue Impact | ${results.get('avg_impact', 0):,.2f} |",
            "",
        ]
        if results.get("business_rules"):
            lines.append("### Business Rule Violations")
            for rule, count in results["business_rules"].items():
                lines.append(f"- **{rule}**: {count}")
            lines.append("")

    # KPI
    if "kpi" in results:
        kpi = results["kpi"]
        lines += [
            "## 4. Key Performance Indicators",
            f"| KPI | Value |",
            f"|-----|-------|",
            f"| Total Sales | ${kpi.get('Total_Sales', 0):,.2f} |",
            f"| Total Profit | ${kpi.get('Total_Profit', 0):,.2f} |",
            f"| Total Orders | {kpi.get('Total_Orders', 0):,} |",
            f"| AOV | ${kpi.get('AOV', 0):,.2f} |",
            f"| Profit Margin | {kpi.get('Profit_Margin_Pct', 0):.2f}% |",
            f"| Win Rate | {kpi.get('Win_Rate_Pct', 0):.2f}% |",
            f"| Avg CLV | ${kpi.get('Avg_CLV', 0):,.2f} |",
            "",
        ]

    lines += [
        "## 5. Output Files",
        "| File | Description |",
        "|------|-------------|",
        "| `output/cleaned_superstore.csv` | Cleaned dataset |",
        "| `output/monthly_sales.csv` | Monthly aggregated + lag features |",
        "| `output/cohort_matrix.csv` | Customer cohort retention table |",
        "| `output/category_metrics.csv` | Category profitability ranking |",
        "| `output/kpi_summary.csv` | Aggregate KPI metrics |",
        "| `output/monthly_sales_arima.csv` | Historical + ARIMA forecast |",
        "| `output/arima_forecast.png` | Forecast Plotly chart |",
        "| `output/anomalies.csv` | Top-50 flagged anomalies |",
        "| `output/anomaly_scatter.png` | Anomaly scatter chart |",
        "| `output/pareto_products.csv` | Pareto product ranking |",
        "| `output/pareto_regions.csv` | Regional revenue breakdown |",
        "| `output/kpi_metrics.csv` | Detailed KPI metrics |",
        "| `output/pareto_waterfall.png` | Waterfall revenue chart |",
        "",
        "---",
        "*ProfitPlus — Superstore Sales Analytics Dashboard*",
    ]

    report = "\n".join(lines)
    report_path = BASE_DIR / "master_report.md"
    report_path.write_text(report, encoding="utf-8")
    return str(report_path)


# ─────────────────────────────────────────────────────────────────────────────
# Argument parsing + main entry
# ─────────────────────────────────────────────────────────────────────────────
def parse_args():
    parser = argparse.ArgumentParser(
        description="ProfitPlus — Superstore Sales Analytics Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --full                  # Run full pipeline
  python main.py --clean                 # Data cleaning only
  python main.py --forecast              # ARIMA forecasting only
  python main.py --anomaly               # Anomaly detection only
  python main.py --pareto                # Pareto analysis only
  python main.py --full --data myfile.csv
        """,
    )
    parser.add_argument("--data", default=DEFAULT_DATASET_PATH,
                        help="Path to the raw Superstore CSV (default: data/superstore.csv)")
    parser.add_argument("--full", action="store_true", help="Run full pipeline")
    parser.add_argument("--clean", action="store_true", help="Run data cleaning step only")
    parser.add_argument("--forecast", action="store_true", help="Run ARIMA forecast only")
    parser.add_argument("--anomaly", action="store_true", help="Run anomaly detection only")
    parser.add_argument("--pareto", action="store_true", help="Run Pareto analysis only")
    return parser.parse_args()


def main():
    args = parse_args()
    logger = setup_logging()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("╔" + "═" * 58 + "╗")
    logger.info("║  ProfitPlus — Superstore Sales Analytics Dashboard      ║")
    logger.info("╚" + "═" * 58 + "╝")

    pipeline_start = time.time()
    results = {}
    validation_errors = []

    # ── Mode selection ───────────────────────────────────────────────────────
    run_full = args.full or not any([args.clean, args.forecast, args.anomaly, args.pareto])

    try:
        # Step 1 — Clean (required for almost everything)
        if run_full or args.clean:
            step_result = step_clean(args.data, logger)
            results.update(step_result)
            df_clean = step_result["df_clean"]

            # Validation
            assert len(df_clean) > 0, "Cleaned dataset is empty!"
            assert "profit_ratio" in df_clean.columns, "Missing profit_ratio column!"
            logger.info("✓ Validation passed: cleaned dataset OK")

        # Step 2 — Features
        if run_full:
            step_result = step_features(results.get("df_clean"), logger)
            results.update(step_result)

        # Step 3 — ARIMA
        if run_full or args.forecast:
            monthly_path = OUTPUT_DIR / "monthly_sales.csv"
            if not monthly_path.exists():
                logger.error("monthly_sales.csv not found. Run --clean first to generate features.")
                sys.exit(1)
            step_result = step_arima(logger)
            results.update(step_result)

        # Step 4 — Anomaly
        if run_full or args.anomaly:
            cleaned_path = OUTPUT_DIR / "cleaned_superstore.csv"
            if not cleaned_path.exists():
                logger.error("cleaned_superstore.csv not found. Run --clean first.")
                sys.exit(1)
            step_result = step_anomaly(logger)
            results.update(step_result)

        # Step 5 — Pareto
        if run_full or args.pareto:
            step_result = step_pareto(logger)
            results.update(step_result)

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        logger.error("Please ensure the Superstore CSV is placed in the data/ folder.")
        logger.error("Download from: https://www.kaggle.com/datasets/thuandao/superstore-sales-analytics")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        sys.exit(1)

    # ── Master report ────────────────────────────────────────────────────────
    if run_full:
        total_elapsed = time.time() - pipeline_start
        report_path = generate_master_report(results, total_elapsed)
        logger.info(f"\n📄 Master report saved: {report_path}")

    total_time = time.time() - pipeline_start
    logger.info("")
    logger.info("╔" + "═" * 58 + "╗")
    logger.info(f"║  ✅ Pipeline completed in {total_time:.1f}s".ljust(60) + "║")
    logger.info("╚" + "═" * 58 + "╝")


if __name__ == "__main__":
    main()

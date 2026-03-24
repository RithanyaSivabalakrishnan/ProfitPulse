"""
Module 3: Feature Engineering
ProfitPlus — Superstore Sales Analytics Dashboard
"""

import logging
import os
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Monthly aggregation
# ─────────────────────────────────────────────────────────────────────────────
def build_monthly_sales(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate data by Year-Month.
    Returns monthly_sales DataFrame with rolling averages and lag features.
    """
    df = df.copy()
    df["Year"] = df["Order Date"].dt.year
    df["Month"] = df["Order Date"].dt.month
    df["YearMonth"] = df["Order Date"].dt.to_period("M")

    monthly = (
        df.groupby("YearMonth")
        .agg(
            Sales=("Sales", "sum"),
            Profit=("Profit", "sum"),
            Orders=("Order ID", "nunique"),
            Quantity=("Quantity", "sum"),
        )
        .reset_index()
        .sort_values("YearMonth")
    )
    monthly["YearMonth"] = monthly["YearMonth"].astype(str)

    logger.info(f"Monthly aggregation: {len(monthly)} months")

    # ── Rolling features (3-month moving average) ───────────────────────────
    for col in ["Sales", "Profit"]:
        monthly[f"{col}_MA3"] = monthly[col].rolling(window=3, min_periods=1).mean().round(2)

    logger.info("Added 3-month rolling averages.")

    # ── Lag features ────────────────────────────────────────────────────────
    for lag in [1, 3, 6]:
        monthly[f"Sales_Lag{lag}"] = monthly["Sales"].shift(lag)
        monthly[f"Profit_Lag{lag}"] = monthly["Profit"].shift(lag)

    logger.info("Added lag features (1, 3, 6 months).")

    # Time-series validation: ensure no future leakage (lags only reference past)
    assert monthly["Sales_Lag1"].iloc[0] is np.nan or pd.isna(monthly["Sales_Lag1"].iloc[0]), \
        "Lag1 first row should be NaN — possible future leak!"

    return monthly


# ─────────────────────────────────────────────────────────────────────────────
# 2. Cohort analysis
# ─────────────────────────────────────────────────────────────────────────────
def build_cohort_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a customer cohort retention table.
    Cohort = month of customer's first order.
    Shows total revenue by cohort × order-month index.
    """
    df = df.copy()
    df["OrderPeriod"] = df["Order Date"].dt.to_period("M")
    df["CohortMonth"] = df.groupby("Customer ID")["Order Date"].transform("min").dt.to_period("M")
    df["PeriodIndex"] = (df["OrderPeriod"] - df["CohortMonth"]).apply(lambda x: x.n)

    cohort = (
        df.groupby(["CohortMonth", "PeriodIndex"])
        .agg(Revenue=("Sales", "sum"))
        .reset_index()
    )
    cohort_matrix = cohort.pivot(index="CohortMonth", columns="PeriodIndex", values="Revenue").fillna(0)
    cohort_matrix.index = cohort_matrix.index.astype(str)
    cohort_matrix.columns = [f"Month_{i}" for i in cohort_matrix.columns]

    logger.info(f"Cohort matrix: {cohort_matrix.shape[0]} cohorts × {cohort_matrix.shape[1]} periods")
    return cohort_matrix.reset_index().rename(columns={"CohortMonth": "Cohort_Month"})


# ─────────────────────────────────────────────────────────────────────────────
# 3. Category profitability ranking
# ─────────────────────────────────────────────────────────────────────────────
def build_category_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Compute sales and profitability metrics per Category and Sub-Category."""
    cat_metrics = (
        df.groupby(["Category", "Sub-Category"])
        .agg(
            Total_Sales=("Sales", "sum"),
            Total_Profit=("Profit", "sum"),
            Total_Orders=("Order ID", "nunique"),
            Total_Quantity=("Quantity", "sum"),
            Avg_Discount=("Discount", "mean"),
        )
        .reset_index()
    )
    cat_metrics["Profit_Margin"] = (cat_metrics["Total_Profit"] / cat_metrics["Total_Sales"]).round(4)
    cat_metrics["Profit_Rank"] = cat_metrics["Total_Profit"].rank(ascending=False).astype(int)
    cat_metrics = cat_metrics.sort_values("Profit_Rank")

    logger.info(f"Category metrics: {len(cat_metrics)} sub-category rows")
    return cat_metrics


# ─────────────────────────────────────────────────────────────────────────────
# 4. KPI summary
# ─────────────────────────────────────────────────────────────────────────────
def build_kpi_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Compute overall KPI metrics."""
    total_sales = df["Sales"].sum()
    total_profit = df["Profit"].sum()
    total_orders = df["Order ID"].nunique()
    total_customers = df["Customer ID"].nunique()
    total_qty = df["Quantity"].sum()
    aov = total_sales / total_orders if total_orders else 0
    profit_margin = total_profit / total_sales if total_sales else 0
    win_rate = (df["Profit"] > 0).mean()

    kpis = pd.DataFrame([{
        "Total_Sales": round(total_sales, 2),
        "Total_Profit": round(total_profit, 2),
        "Total_Orders": total_orders,
        "Total_Customers": total_customers,
        "Total_Quantity": int(total_qty),
        "AOV": round(aov, 2),
        "Profit_Margin_Pct": round(profit_margin * 100, 2),
        "Win_Rate_Pct": round(win_rate * 100, 2),
    }])
    logger.info(f"KPI Summary — Sales: ${total_sales:,.0f}, Profit: ${total_profit:,.0f}, AOV: ${aov:,.2f}")
    return kpis


# ─────────────────────────────────────────────────────────────────────────────
# 5. Main orchestration function
# ─────────────────────────────────────────────────────────────────────────────
def engineer_features(df_clean: pd.DataFrame, output_dir: str = "output") -> dict:
    """
    Run the feature engineering pipeline and export 4 CSVs.

    Returns
    -------
    dict of {name: pd.DataFrame}
    """
    os.makedirs(output_dir, exist_ok=True)
    logger.info("=" * 60)
    logger.info("Starting Feature Engineering Pipeline")
    logger.info("=" * 60)

    outputs = {}

    logger.info("[Step 1] Building monthly sales…")
    monthly = build_monthly_sales(df_clean)
    monthly.to_csv(os.path.join(output_dir, "monthly_sales.csv"), index=False)
    outputs["monthly_sales"] = monthly
    logger.info(f"  → monthly_sales.csv saved ({len(monthly)} rows)")

    logger.info("[Step 2] Building cohort matrix…")
    cohort = build_cohort_matrix(df_clean)
    cohort.to_csv(os.path.join(output_dir, "cohort_matrix.csv"), index=False)
    outputs["cohort_matrix"] = cohort
    logger.info(f"  → cohort_matrix.csv saved ({len(cohort)} rows)")

    logger.info("[Step 3] Building category metrics…")
    cat_metrics = build_category_metrics(df_clean)
    cat_metrics.to_csv(os.path.join(output_dir, "category_metrics.csv"), index=False)
    outputs["category_metrics"] = cat_metrics
    logger.info(f"  → category_metrics.csv saved ({len(cat_metrics)} rows)")

    logger.info("[Step 4] Building KPI summary…")
    kpi_summary = build_kpi_summary(df_clean)
    kpi_summary.to_csv(os.path.join(output_dir, "kpi_summary.csv"), index=False)
    outputs["kpi_summary"] = kpi_summary
    logger.info(f"  → kpi_summary.csv saved")

    logger.info("=" * 60)
    logger.info("Feature Engineering Complete — 4 CSVs exported")
    logger.info("=" * 60)
    return outputs

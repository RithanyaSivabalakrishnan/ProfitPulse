"""
Module 3: Feature Engineering
ProfitPlus — Superstore Sales Analytics Dashboard
Columns: order_id, order_date, customer_name, sales, profit, quantity, category, sub_category, region, etc.
"""

import logging
import os
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def build_monthly_sales(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["year_month"] = df["order_date"].dt.to_period("M")

    monthly = (
        df.groupby("year_month")
        .agg(
            Sales=("sales", "sum"),
            Profit=("profit", "sum"),
            Orders=("order_id", "nunique"),
            Quantity=("quantity", "sum"),
        )
        .reset_index()
        .sort_values("year_month")
    )
    monthly["YearMonth"] = monthly["year_month"].astype(str)
    monthly = monthly.drop(columns=["year_month"])

    logger.info(f"Monthly aggregation: {len(monthly)} months")

    # 3-month rolling averages
    for col in ["Sales", "Profit"]:
        monthly[f"{col}_MA3"] = monthly[col].rolling(window=3, min_periods=1).mean().round(2)

    # Lag features (1, 3, 6 months)
    for lag in [1, 3, 6]:
        monthly[f"Sales_Lag{lag}"] = monthly["Sales"].shift(lag)
        monthly[f"Profit_Lag{lag}"] = monthly["Profit"].shift(lag)

    logger.info("Added rolling averages and lag features.")
    return monthly


def build_cohort_matrix(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["order_period"] = df["order_date"].dt.to_period("M")

    # Customer's first order month = cohort
    df["cohort_month"] = df.groupby("customer_name")["order_date"].transform("min").dt.to_period("M")
    df["period_index"] = (df["order_period"] - df["cohort_month"]).apply(lambda x: x.n)

    cohort = (
        df.groupby(["cohort_month", "period_index"])
        .agg(Revenue=("sales", "sum"))
        .reset_index()
    )
    cohort_matrix = cohort.pivot(index="cohort_month", columns="period_index", values="Revenue").fillna(0)
    cohort_matrix.index = cohort_matrix.index.astype(str)
    cohort_matrix.columns = [f"Month_{i}" for i in cohort_matrix.columns]

    logger.info(f"Cohort matrix: {cohort_matrix.shape[0]} cohorts × {cohort_matrix.shape[1]} periods")
    return cohort_matrix.reset_index().rename(columns={"cohort_month": "Cohort_Month"})


def build_category_metrics(df: pd.DataFrame) -> pd.DataFrame:
    sub_col = "sub_category" if "sub_category" in df.columns else "sub-category"
    cat_metrics = (
        df.groupby(["category", sub_col])
        .agg(
            Total_Sales=("sales", "sum"),
            Total_Profit=("profit", "sum"),
            Total_Orders=("order_id", "nunique"),
            Total_Quantity=("quantity", "sum"),
            Avg_Discount=("discount", "mean"),
        )
        .reset_index()
    )
    cat_metrics["Profit_Margin"] = (cat_metrics["Total_Profit"] / cat_metrics["Total_Sales"]).round(4)
    cat_metrics["Profit_Rank"] = cat_metrics["Total_Profit"].rank(ascending=False).astype(int)
    cat_metrics = cat_metrics.sort_values("Profit_Rank")
    logger.info(f"Category metrics: {len(cat_metrics)} sub-category rows")
    return cat_metrics


def build_kpi_summary(df: pd.DataFrame) -> pd.DataFrame:
    total_sales = df["sales"].sum()
    total_profit = df["profit"].sum()
    total_orders = df["order_id"].nunique()
    total_qty = df["quantity"].sum()
    aov = total_sales / total_orders if total_orders else 0
    profit_margin = total_profit / total_sales if total_sales else 0
    win_rate = (df["profit"] > 0).mean()

    kpis = pd.DataFrame([{
        "Total_Sales": round(total_sales, 2),
        "Total_Profit": round(total_profit, 2),
        "Total_Orders": total_orders,
        "Total_Quantity": int(total_qty),
        "AOV": round(aov, 2),
        "Profit_Margin_Pct": round(profit_margin * 100, 2),
        "Win_Rate_Pct": round(win_rate * 100, 2),
    }])
    logger.info(f"KPI — Sales: ${total_sales:,.0f}, Profit: ${total_profit:,.0f}, AOV: ${aov:,.2f}")
    return kpis


def engineer_features(df_clean: pd.DataFrame, output_dir: str = "output") -> dict:
    """Run full feature engineering pipeline, export 4 CSVs."""
    os.makedirs(output_dir, exist_ok=True)
    logger.info("=" * 60)
    logger.info("Starting Feature Engineering Pipeline")
    logger.info("=" * 60)

    outputs = {}

    logger.info("[Step 1] Building monthly sales…")
    monthly = build_monthly_sales(df_clean)
    monthly.to_csv(os.path.join(output_dir, "monthly_sales.csv"), index=False)
    outputs["monthly_sales"] = monthly

    logger.info("[Step 2] Building cohort matrix…")
    cohort = build_cohort_matrix(df_clean)
    cohort.to_csv(os.path.join(output_dir, "cohort_matrix.csv"), index=False)
    outputs["cohort_matrix"] = cohort

    logger.info("[Step 3] Building category metrics…")
    cat = build_category_metrics(df_clean)
    cat.to_csv(os.path.join(output_dir, "category_metrics.csv"), index=False)
    outputs["category_metrics"] = cat

    logger.info("[Step 4] Building KPI summary…")
    kpi = build_kpi_summary(df_clean)
    kpi.to_csv(os.path.join(output_dir, "kpi_summary.csv"), index=False)
    outputs["kpi_summary"] = kpi

    logger.info("=" * 60)
    logger.info("Feature Engineering Complete — 4 CSVs exported")
    logger.info("=" * 60)
    return outputs

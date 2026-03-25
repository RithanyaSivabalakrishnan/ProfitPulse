"""
Module 2: Data Cleaning & Validation
ProfitPlus — Superstore Sales Analytics Dashboard
Columns are snake_case: order_id, order_date, ship_date, sales, profit, quantity, discount, etc.
"""

import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def parse_dates(df):
    for col in ["order_date", "ship_date"]:
        if col in df.columns:
            parsed = pd.to_datetime(df[col], format="%m/%d/%Y", errors="coerce")
            if parsed.notna().mean() < 0.5:
                parsed = pd.to_datetime(df[col], errors="coerce")
            df[col] = parsed
            nulls = int(df[col].isnull().sum())
            if nulls:
                logger.warning(col + ": " + str(nulls) + " unparseable dates, dropping.")
                df = df.dropna(subset=[col])
            mn = df[col].min().date()
            mx = df[col].max().date()
            logger.info(col + ": parsed OK => " + str(mn) + " to " + str(mx))
    return df


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)
    # Deduplicate on order_id + product_id if both exist; else just order_id
    subset = ["order_id", "product_id"] if "product_id" in df.columns else ["order_id"]
    df = df.drop_duplicates(subset=subset, keep="first")
    removed = before - len(df)
    logger.info(f"Duplicates removed: {removed}  (remaining: {len(df):,})")
    return df


def handle_nulls(df: pd.DataFrame) -> pd.DataFrame:
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    datetime_cols = df.select_dtypes(include=["datetime64[ns]", "datetime"]).columns.tolist()

    for col in numeric_cols:
        n = df[col].isnull().sum()
        if n:
            val = df[col].median()
            df[col] = df[col].fillna(val)
            logger.info(f"  {col}: filled {n} nulls with median={val:.4f}")

    for col in categorical_cols:
        n = df[col].isnull().sum()
        if n:
            val = df[col].mode(dropna=True)[0]
            df[col] = df[col].fillna(val)
            logger.info(f"  {col}: filled {n} nulls with mode='{val}'")

    # Datetime nulls: drop remaining (already handled in parse_dates)
    for col in datetime_cols:
        n = df[col].isnull().sum()
        if n:
            df = df.dropna(subset=[col])
            logger.info(f"  {col}: dropped {n} rows with unparseable dates.")

    remaining = df.isnull().sum().sum()
    if remaining > 0:
        logger.warning(f"  {remaining} nulls remain — dropping those rows.")
        df = df.dropna()
    logger.info("All nulls resolved.")
    return df


def remove_outliers_iqr(df: pd.DataFrame,
                         columns: list = None,
                         multiplier: float = 3.0) -> tuple:
    if columns is None:
        columns = ["sales", "profit"]

    outlier_report = {}
    before = len(df)

    for col in columns:
        if col not in df.columns:
            continue
        # Coerce to numeric in case column was read as string
        df[col] = __import__("pandas").to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=[col])
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - multiplier * IQR
        upper = Q3 + multiplier * IQR
        mask = (df[col] < lower) | (df[col] > upper)
        count = int(mask.sum())
        outlier_report[col] = {
            "Q1": round(Q1, 4), "Q3": round(Q3, 4), "IQR": round(IQR, 4),
            "lower_bound": round(lower, 4), "upper_bound": round(upper, 4),
            "outliers_removed": count,
        }
        df = df[~mask]
        logger.info(f"  {col}: removed {count} outliers (bounds [{lower:.2f}, {upper:.2f}])")

    logger.info(f"Outlier removal: {before - len(df)} rows removed, {len(df):,} remain.")
    return df, outlier_report


def add_calculated_columns(df: pd.DataFrame) -> pd.DataFrame:
    # Profit Ratio
    df["profit_ratio"] = np.where(
        df["sales"] != 0,
        (df["profit"] / df["sales"]).round(4),
        0.0
    )
    logger.info("Added 'profit_ratio' column.")

    # Days to Ship
    if "order_date" in df.columns and "ship_date" in df.columns:
        df["days_to_ship"] = (df["ship_date"] - df["order_date"]).dt.days
        neg = (df["days_to_ship"] < 0).sum()
        if neg:
            logger.warning(f"  {neg} rows have negative days_to_ship → setting NaN.")
            df.loc[df["days_to_ship"] < 0, "days_to_ship"] = np.nan
        logger.info(
            f"Added 'days_to_ship'. Mean={df['days_to_ship'].mean():.1f}, "
            f"Max={df['days_to_ship'].max():.0f}"
        )
    return df


def build_quality_report(df_raw, df_clean, outlier_report):
    return {
        "raw_rows": len(df_raw),
        "clean_rows": len(df_clean),
        "rows_removed": len(df_raw) - len(df_clean),
        "columns_raw": len(df_raw.columns),
        "columns_clean": len(df_clean.columns),
        "missing_pct_before": {
            col: round(df_raw[col].isnull().mean() * 100, 2)
            for col in df_raw.columns if df_raw[col].isnull().any()
        },
        "duplicates_before": int(
            df_raw.duplicated(
                subset=["order_id", "product_id"] if "product_id" in df_raw.columns else ["order_id"]
            ).sum()
        ),
        "outlier_report": outlier_report,
        "new_columns": [c for c in df_clean.columns if c not in df_raw.columns],
    }


def clean_data(df_raw: pd.DataFrame, output_path: str = "output/cleaned_superstore.csv") -> tuple:
    """Full cleaning pipeline. Returns (df_clean, quality_report)."""
    import os
    logger.info("=" * 60)
    logger.info("Starting Data Cleaning Pipeline")
    logger.info("=" * 60)

    df = df_raw.copy()

    logger.info("[Step 1] Parsing dates…")
    df = parse_dates(df)

    logger.info("[Step 2] Removing duplicates…")
    df = remove_duplicates(df)

    logger.info("[Step 3] Handling nulls…")
    df = handle_nulls(df)

    logger.info("[Step 4] Removing outliers (IQR × 3σ)…")
    df, outlier_report = remove_outliers_iqr(df, columns=["sales", "profit"], multiplier=3.0)

    logger.info("[Step 5] Adding calculated columns…")
    df = add_calculated_columns(df)

    logger.info("[Step 6] Building quality report…")
    quality_report = build_quality_report(df_raw, df, outlier_report)

    logger.info("[Step 7] Saving cleaned dataset…")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    logger.info(f"Saved: {output_path}  ({len(df):,} rows × {len(df.columns)} columns)")

    logger.info("=" * 60)
    logger.info("Data Cleaning Complete")
    logger.info("=" * 60)
    return df, quality_report

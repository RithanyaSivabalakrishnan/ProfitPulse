"""
Module 2: Data Cleaning & Validation
ProfitPlus — Superstore Sales Analytics Dashboard
"""

import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Date parsing
# ─────────────────────────────────────────────────────────────────────────────
def parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Parse Order Date and Ship Date columns to datetime."""
    for col in ["Order Date", "Ship Date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], infer_datetime_format=True, errors="coerce")
            nulls = df[col].isnull().sum()
            if nulls:
                logger.warning(f"{col}: {nulls} values could not be parsed.")
            else:
                logger.info(f"{col}: parsed successfully → range {df[col].min().date()} to {df[col].max().date()}")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 2. Duplicate removal
# ─────────────────────────────────────────────────────────────────────────────
def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicate rows (same Order ID + Product ID)."""
    before = len(df)
    df = df.drop_duplicates(subset=["Order ID", "Product ID"], keep="first")
    removed = before - len(df)
    if removed:
        logger.warning(f"Removed {removed} duplicate rows.")
    else:
        logger.info("No duplicate rows found.")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 3. Null handling
# ─────────────────────────────────────────────────────────────────────────────
def handle_nulls(df: pd.DataFrame) -> pd.DataFrame:
    """Fill numeric nulls with median, categorical nulls with mode."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    for col in numeric_cols:
        n = df[col].isnull().sum()
        if n:
            median_val = df[col].median()
            df[col].fillna(median_val, inplace=True)
            logger.info(f"  {col}: filled {n} nulls with median={median_val:.4f}")

    for col in categorical_cols:
        n = df[col].isnull().sum()
        if n:
            mode_val = df[col].mode(dropna=True)[0]
            df[col].fillna(mode_val, inplace=True)
            logger.info(f"  {col}: filled {n} nulls with mode='{mode_val}'")

    assert df.isnull().sum().sum() == 0, "Nulls still remain after imputation!"
    logger.info("All nulls resolved.")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 4. Outlier removal (IQR method)
# ─────────────────────────────────────────────────────────────────────────────
def remove_outliers_iqr(df: pd.DataFrame,
                         columns: list = None,
                         multiplier: float = 3.0) -> tuple[pd.DataFrame, dict]:
    """
    Remove outliers using IQR method on the given columns.
    Default columns: Sales, Profit.
    multiplier=3.0 corresponds to ~99.7% of data (very conservative).
    """
    if columns is None:
        columns = ["Sales", "Profit"]

    outlier_report = {}
    before = len(df)

    for col in columns:
        if col not in df.columns:
            continue
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - multiplier * IQR
        upper = Q3 + multiplier * IQR
        mask = (df[col] < lower) | (df[col] > upper)
        count = mask.sum()
        outlier_report[col] = {
            "Q1": round(Q1, 4),
            "Q3": round(Q3, 4),
            "IQR": round(IQR, 4),
            "lower_bound": round(lower, 4),
            "upper_bound": round(upper, 4),
            "outliers_removed": int(count),
        }
        df = df[~mask]
        logger.info(f"  {col}: removed {count} outliers (bounds [{lower:.2f}, {upper:.2f}])")

    after = len(df)
    logger.info(f"Outlier removal: {before - after} rows removed, {after:,} rows remain.")
    return df, outlier_report


# ─────────────────────────────────────────────────────────────────────────────
# 5. Calculated columns
# ─────────────────────────────────────────────────────────────────────────────
def add_calculated_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add Profit Ratio and Days to Ship derived columns."""
    # Profit Ratio = Profit / Sales  (handle division by zero)
    df["Profit Ratio"] = np.where(
        df["Sales"] != 0,
        (df["Profit"] / df["Sales"]).round(4),
        0.0
    )
    logger.info("Added 'Profit Ratio' column.")

    # Days to Ship = Ship Date - Order Date
    if "Order Date" in df.columns and "Ship Date" in df.columns:
        df["Days to Ship"] = (df["Ship Date"] - df["Order Date"]).dt.days
        # Sanity check: negative days to ship should not exist
        neg = (df["Days to Ship"] < 0).sum()
        if neg:
            logger.warning(f"  {neg} rows have negative Days to Ship — setting to NaN.")
            df.loc[df["Days to Ship"] < 0, "Days to Ship"] = np.nan
        logger.info(
            f"Added 'Days to Ship' column. "
            f"Mean={df['Days to Ship'].mean():.1f}, Max={df['Days to Ship'].max():.0f}"
        )
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 6. Data quality report
# ─────────────────────────────────────────────────────────────────────────────
def build_quality_report(df_raw: pd.DataFrame,
                          df_clean: pd.DataFrame,
                          outlier_report: dict) -> dict:
    """Generate a data quality report comparing raw vs cleaned dataset."""
    report = {
        "raw_rows": len(df_raw),
        "clean_rows": len(df_clean),
        "rows_removed": len(df_raw) - len(df_clean),
        "columns_raw": len(df_raw.columns),
        "columns_clean": len(df_clean.columns),
        "missing_pct_before": {
            col: round(df_raw[col].isnull().mean() * 100, 2)
            for col in df_raw.columns if df_raw[col].isnull().any()
        },
        "duplicates_before": int(df_raw.duplicated(subset=["Order ID", "Product ID"]).sum()),
        "outlier_report": outlier_report,
        "new_columns": [c for c in df_clean.columns if c not in df_raw.columns],
    }
    return report


# ─────────────────────────────────────────────────────────────────────────────
# 7. Main orchestration function
# ─────────────────────────────────────────────────────────────────────────────
def clean_data(df_raw: pd.DataFrame, output_path: str = "output/cleaned_superstore.csv") -> tuple:
    """
    Run the full cleaning pipeline on the raw Superstore dataframe.

    Returns
    -------
    df_clean : pd.DataFrame
    quality_report : dict
    """
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
    df, outlier_report = remove_outliers_iqr(df, columns=["Sales", "Profit"], multiplier=3.0)

    logger.info("[Step 5] Adding calculated columns…")
    df = add_calculated_columns(df)

    logger.info("[Step 6] Building quality report…")
    quality_report = build_quality_report(df_raw, df, outlier_report)

    logger.info("[Step 7] Saving cleaned dataset…")
    import os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    logger.info(f"Saved: {output_path}  ({len(df):,} rows × {len(df.columns)} columns)")

    logger.info("=" * 60)
    logger.info("Data Cleaning Complete")
    logger.info("=" * 60)

    return df, quality_report

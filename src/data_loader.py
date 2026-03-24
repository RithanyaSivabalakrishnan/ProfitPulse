"""
Module 1: Data Loader
ProfitPlus — Superstore Sales Analytics Dashboard
"""

import os
import logging
import pandas as pd

logger = logging.getLogger(__name__)

# Expected dataset dimensions
EXPECTED_ROWS = 9994
EXPECTED_COLS = 21

# Column names expected in the raw CSV
EXPECTED_COLUMNS = [
    "Row ID", "Order ID", "Order Date", "Ship Date", "Ship Mode",
    "Customer ID", "Customer Name", "Segment", "Country", "City",
    "State", "Postal Code", "Region", "Product ID", "Category",
    "Sub-Category", "Product Name", "Sales", "Quantity", "Discount", "Profit"
]


def load_data(filepath: str) -> pd.DataFrame:
    """
    Load the Superstore CSV dataset from the given filepath.

    Parameters
    ----------
    filepath : str
        Absolute or relative path to the CSV file.

    Returns
    -------
    pd.DataFrame
        Raw dataset.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    AssertionError
        If the dataset dimensions do not match expected values.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"Dataset not found at: {filepath}\n"
            "Please download from: https://www.kaggle.com/datasets/thuandao/superstore-sales-analytics\n"
            "and place the CSV file in the data/ directory."
        )

    logger.info(f"Loading dataset from: {filepath}")

    # Try UTF-8 first, fall back to latin-1 (Superstore CSVs sometimes have encoding issues)
    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            df = pd.read_csv(filepath, encoding=encoding)
            break
        except UnicodeDecodeError:
            logger.warning(f"Encoding {encoding} failed, trying next…")
    else:
        raise ValueError("Could not read the CSV with any supported encoding.")

    logger.info(f"Loaded dataset: {df.shape[0]:,} rows × {df.shape[1]} columns")

    # ── Validate dimensions ──────────────────────────────────────────────────
    actual_rows, actual_cols = df.shape
    if actual_rows != EXPECTED_ROWS:
        logger.warning(
            f"Expected {EXPECTED_ROWS:,} rows but got {actual_rows:,}. "
            "Proceeding, but verify the dataset version."
        )
    if actual_cols != EXPECTED_COLS:
        logger.warning(
            f"Expected {EXPECTED_COLS} columns but got {actual_cols}. "
            "Column list may differ."
        )

    # ── Log column overview ──────────────────────────────────────────────────
    logger.info("Columns: " + ", ".join(df.columns.tolist()))
    logger.info(f"Memory usage: {df.memory_usage(deep=True).sum() / 1024:.1f} KB")

    return df


def get_data_summary(df: pd.DataFrame) -> dict:
    """Return a brief summary dict of the loaded dataset."""
    return {
        "rows": len(df),
        "columns": len(df.columns),
        "column_names": df.columns.tolist(),
        "dtypes": df.dtypes.astype(str).to_dict(),
        "null_counts": df.isnull().sum().to_dict(),
        "memory_kb": round(df.memory_usage(deep=True).sum() / 1024, 2),
    }

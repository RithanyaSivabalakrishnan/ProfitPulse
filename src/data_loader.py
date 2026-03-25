"""
Module 1: Data Loader
ProfitPlus — Superstore Sales Analytics Dashboard
Actual dataset: SuperStoreOrders - SuperStoreOrders.csv (21 columns, snake_case headers)
"""

import os
import logging
import pandas as pd

logger = logging.getLogger(__name__)

EXPECTED_COLS = 21

# Actual columns in the dataset (snake_case)
EXPECTED_COLUMNS = [
    "order_id", "order_date", "ship_date", "ship_mode", "customer_name",
    "segment", "state", "country", "market", "region", "product_id",
    "category", "sub_category", "product_name", "sales", "quantity",
    "discount", "profit", "shipping_cost", "order_priority", "year"
]

# Default dataset filename
DEFAULT_FILENAME = "SuperStoreOrders - SuperStoreOrders.csv"


def load_data(filepath: str) -> pd.DataFrame:
    """
    Load the Superstore CSV dataset.

    Parameters
    ----------
    filepath : str
        Path to the CSV file.

    Returns
    -------
    pd.DataFrame
        Raw dataset.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"Dataset not found at: {filepath}\n"
            "Please ensure the CSV is in the data/ directory."
        )

    logger.info(f"Loading dataset from: {filepath}")

    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            df = pd.read_csv(filepath, encoding=encoding)
            break
        except UnicodeDecodeError:
            logger.warning(f"Encoding {encoding} failed, trying next…")
    else:
        raise ValueError("Could not read the CSV with any supported encoding.")

    # Normalize column names to lowercase strip whitespace
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_").str.replace("-", "_")

    actual_rows, actual_cols = df.shape
    logger.info(f"Loaded: {actual_rows:,} rows × {actual_cols} columns")
    logger.info("Columns: " + ", ".join(df.columns.tolist()))

    # Ensure numeric columns are properly typed (CSV sometimes reads them as str)
    for col in ["sales", "quantity", "discount", "profit", "shipping_cost"]:
        if col in df.columns:
            df[col] = __import__("pandas").to_numeric(df[col], errors="coerce")

    if actual_cols != EXPECTED_COLS:
        logger.warning(f"Expected {EXPECTED_COLS} columns but got {actual_cols}.")

    return df


def get_data_summary(df: pd.DataFrame) -> dict:
    return {
        "rows": len(df),
        "columns": len(df.columns),
        "column_names": df.columns.tolist(),
        "null_counts": df.isnull().sum().to_dict(),
        "memory_kb": round(df.memory_usage(deep=True).sum() / 1024, 2),
    }

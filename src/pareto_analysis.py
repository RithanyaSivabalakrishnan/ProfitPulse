"""
Module 6: Pareto Analysis & KPIs
ProfitPlus — Superstore Sales Analytics Dashboard
Column names: sales, profit, quantity, order_id, product_id, product_name, category, sub_category, region, state, discount
"""

import logging
import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go

logger = logging.getLogger(__name__)


def pareto_products(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pareto analysis at the product_id level.
    product_id is guaranteed unique — required for PowerBI many-to-one relationship.
    Dimension columns (product_name, category, sub_category) are taken as the
    first occurrence per product_id.
    """
    sub_col = "sub_category" if "sub_category" in df.columns else "sub-category"

    # Step 1: Aggregate metrics by product_id only (guarantees uniqueness)
    product_rev = (
        df.groupby("product_id")
        .agg(
            Revenue=("sales", "sum"),
            Profit=("profit", "sum"),
            Orders=("order_id", "nunique"),
            Quantity=("quantity", "sum"),
        )
        .reset_index()
        .sort_values("Revenue", ascending=False)
        .reset_index(drop=True)
    )

    # Step 2: Join dimension attributes (first occurrence per product_id)
    dim_cols = ["product_id"]
    for col in ["product_name", "category", sub_col]:
        if col in df.columns:
            dim_cols.append(col)
    dim = df[dim_cols].drop_duplicates(subset=["product_id"], keep="first")
    product_rev = product_rev.merge(dim, on="product_id", how="left")

    # Step 3: Cumulative / Pareto metrics
    total = product_rev["Revenue"].sum()
    product_rev["Cumulative_Revenue"] = product_rev["Revenue"].cumsum()
    product_rev["Cumulative_Revenue_Pct"] = (product_rev["Cumulative_Revenue"] / total * 100).round(2)
    product_rev["Revenue_Share_Pct"] = (product_rev["Revenue"] / total * 100).round(4)
    product_rev["Is_Top20_Pct"] = ((product_rev.index + 1) / len(product_rev) * 100) <= 20
    product_rev["Rank"] = range(1, len(product_rev) + 1)

    # Validate uniqueness
    assert product_rev["product_id"].is_unique, "product_id still not unique after dedup!"

    top20 = product_rev[product_rev["Is_Top20_Pct"]]
    logger.info(
        f"Top 20% products ({len(top20)} unique IDs): "
        f"${top20['Revenue'].sum():,.0f} ({top20['Revenue'].sum()/total*100:.1f}% of total)"
    )
    logger.info(f"Total unique product_ids: {len(product_rev)} — ready for PowerBI relationship")
    return product_rev



def pareto_regions(df: pd.DataFrame) -> pd.DataFrame:
    region_cols = [c for c in ["region", "state"] if c in df.columns]
    if not region_cols:
        region_cols = ["market"]

    region_rev = (
        df.groupby(region_cols)
        .agg(Revenue=("sales", "sum"), Profit=("profit", "sum"),
             Orders=("order_id", "nunique"),
             Customers=("customer_name", "nunique"))
        .reset_index()
        .sort_values("Revenue", ascending=False)
    )
    total = region_rev["Revenue"].sum()
    region_rev["Revenue_Share_Pct"] = (region_rev["Revenue"] / total * 100).round(2)
    region_rev["Profit_Margin_Pct"] = (region_rev["Profit"] / region_rev["Revenue"] * 100).round(2)
    region_rev["Rank"] = range(1, len(region_rev) + 1)
    logger.info(f"Region analysis: {len(region_rev)} rows")
    return region_rev


def build_kpi_metrics(df: pd.DataFrame) -> pd.DataFrame:
    total_sales = df["sales"].sum()
    total_profit = df["profit"].sum()
    total_orders = df["order_id"].nunique()
    total_qty = df["quantity"].sum()

    order_sales = df.groupby("order_id")["sales"].sum()
    aov = order_sales.mean()
    profit_margin = (total_profit / total_sales) * 100 if total_sales else 0

    clv = df.groupby("customer_name")["sales"].sum()
    order_profit = df.groupby("order_id")["profit"].sum()
    win_rate = (order_profit > 0).mean() * 100

    kpis = pd.DataFrame([{
        "Total_Sales": round(total_sales, 2),
        "Total_Profit": round(total_profit, 2),
        "Total_Orders": int(total_orders),
        "Total_Quantity": int(total_qty),
        "AOV": round(float(aov), 2),
        "Profit_Margin_Pct": round(profit_margin, 2),
        "Avg_CLV": round(float(clv.mean()), 2),
        "Max_CLV": round(float(clv.max()), 2),
        "Win_Rate_Pct": round(float(win_rate), 2),
    }])
    logger.info(f"KPIs — Sales: ${total_sales:,.0f}, Margin: {profit_margin:.1f}%, AOV: ${aov:,.2f}")
    return kpis


def create_pareto_waterfall(product_rev: pd.DataFrame, output_path: str, top_n: int = 15) -> None:
    top = product_rev.head(top_n).copy()
    others = product_rev.iloc[top_n:]["Revenue"].sum()

    # Use product_name if available, else category
    label_col = "product_name" if "product_name" in top.columns else "category"
    names = top[label_col].astype(str).str[:30].tolist() + ["All Others"]
    values = top["Revenue"].tolist() + [others]

    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["relative"] * len(names),
        x=names,
        y=values,
        textposition="outside",
        text=[f"${v:,.0f}" for v in values],
        connector=dict(line=dict(color="#2a1f47", width=1)),
        increasing=dict(marker=dict(color="#a855f7")),
        decreasing=dict(marker=dict(color="#e040a0")),
    ))

    fig.update_layout(
        title=dict(text=f"<b>Pareto Revenue Waterfall — Top {top_n} Products</b>",
                   font=dict(size=17, color="#f0e8ff")),
        paper_bgcolor="#0a0612", plot_bgcolor="#110d1f",
        font=dict(color="#9d8dc0"),
        xaxis=dict(title="Product", gridcolor="#1c1535", tickangle=-40),
        yaxis=dict(title="Revenue ($)", gridcolor="#1c1535", tickprefix="$"),
        width=1400, height=600,
        showlegend=False,
    )

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    try:
        fig.write_image(output_path)
        logger.info(f"Waterfall chart saved: {output_path}")
    except Exception as e:
        logger.warning(f"PNG save failed ({e}), saving HTML fallback.")
        fig.write_html(output_path.replace(".png", ".html"))


def run_pareto_analysis(cleaned_path: str = "output/cleaned_superstore.csv",
                         output_dir: str = "output") -> dict:
    os.makedirs(output_dir, exist_ok=True)
    logger.info("=" * 60)
    logger.info("Starting Pareto Analysis & KPI Pipeline")
    logger.info("=" * 60)

    df = pd.read_csv(cleaned_path)

    prod = pareto_products(df)
    prod_path = os.path.join(output_dir, "pareto_products.csv")
    prod.to_csv(prod_path, index=False)

    reg = pareto_regions(df)
    reg_path = os.path.join(output_dir, "pareto_regions.csv")
    reg.to_csv(reg_path, index=False)

    kpi = build_kpi_metrics(df)
    kpi_path = os.path.join(output_dir, "kpi_metrics.csv")
    kpi.to_csv(kpi_path, index=False)

    waterfall_path = os.path.join(output_dir, "pareto_waterfall.png")
    create_pareto_waterfall(prod, waterfall_path, top_n=15)

    logger.info("=" * 60)
    logger.info("Pareto Analysis Complete")
    logger.info("=" * 60)

    return {
        "pareto_products_csv": prod_path,
        "pareto_regions_csv": reg_path,
        "kpi_metrics_csv": kpi_path,
        "waterfall_chart": waterfall_path,
        "kpi": kpi.to_dict(orient="records")[0],
    }

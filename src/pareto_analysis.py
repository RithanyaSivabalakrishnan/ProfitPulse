"""
Module 6: Pareto Analysis & KPIs
ProfitPlus — Superstore Sales Analytics Dashboard
"""

import logging
import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Pareto analysis — Products
# ─────────────────────────────────────────────────────────────────────────────
def pareto_products(df: pd.DataFrame) -> pd.DataFrame:
    """
    Identify the top 20% products that contribute ~80% of revenue.
    Returns ranked product table with cumulative revenue %.
    """
    product_rev = (
        df.groupby(["Product ID", "Product Name", "Category", "Sub-Category"])
        .agg(
            Revenue=("Sales", "sum"),
            Profit=("Profit", "sum"),
            Orders=("Order ID", "nunique"),
            Quantity=("Quantity", "sum"),
        )
        .reset_index()
        .sort_values("Revenue", ascending=False)
    )

    product_rev["Cumulative_Revenue"] = product_rev["Revenue"].cumsum()
    total = product_rev["Revenue"].sum()
    product_rev["Cumulative_Revenue_Pct"] = (product_rev["Cumulative_Revenue"] / total * 100).round(2)
    product_rev["Revenue_Share_Pct"] = (product_rev["Revenue"] / total * 100).round(4)
    product_rev["Is_Top20_Pct"] = (
        (product_rev.index + 1) / len(product_rev) * 100
    ) <= 20
    product_rev["Rank"] = range(1, len(product_rev) + 1)

    top_20_pct_products = product_rev[product_rev["Is_Top20_Pct"]]
    top_revenue = top_20_pct_products["Revenue"].sum()
    logger.info(
        f"Top 20% products ({len(top_20_pct_products)} items): "
        f"${top_revenue:,.0f} revenue ({top_revenue/total*100:.1f}% of total)"
    )
    return product_rev


# ─────────────────────────────────────────────────────────────────────────────
# 2. Pareto analysis — Regions
# ─────────────────────────────────────────────────────────────────────────────
def pareto_regions(df: pd.DataFrame) -> pd.DataFrame:
    """Revenue and profit breakdown by Region and State."""
    region_rev = (
        df.groupby(["Region", "State"])
        .agg(
            Revenue=("Sales", "sum"),
            Profit=("Profit", "sum"),
            Orders=("Order ID", "nunique"),
            Customers=("Customer ID", "nunique"),
        )
        .reset_index()
        .sort_values("Revenue", ascending=False)
    )
    total = region_rev["Revenue"].sum()
    region_rev["Revenue_Share_Pct"] = (region_rev["Revenue"] / total * 100).round(2)
    region_rev["Profit_Margin_Pct"] = (region_rev["Profit"] / region_rev["Revenue"] * 100).round(2)
    region_rev["Rank"] = range(1, len(region_rev) + 1)
    logger.info(f"Region analysis: {len(region_rev)} region-state combinations")
    return region_rev


# ─────────────────────────────────────────────────────────────────────────────
# 3. KPI metrics
# ─────────────────────────────────────────────────────────────────────────────
def build_kpi_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute transaction-level and aggregate KPI metrics.
    """
    total_sales = df["Sales"].sum()
    total_profit = df["Profit"].sum()
    total_orders = df["Order ID"].nunique()
    total_qty = df["Quantity"].sum()

    # AOV = Average Order Value
    order_sales = df.groupby("Order ID")["Sales"].sum()
    aov = order_sales.mean()

    # Profit Margin %
    profit_margin = (total_profit / total_sales) * 100 if total_sales else 0

    # Customer Lifetime Value
    clv = df.groupby("Customer ID")["Sales"].sum()

    # Win Rate = % orders with positive profit
    order_profit = df.groupby("Order ID")["Profit"].sum()
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

    logger.info(
        f"KPIs — Sales: ${total_sales:,.0f}, Profit Margin: {profit_margin:.1f}%, "
        f"AOV: ${aov:,.2f}, Win Rate: {win_rate:.1f}%"
    )
    return kpis


# ─────────────────────────────────────────────────────────────────────────────
# 4. Waterfall chart (Pareto contribution)
# ─────────────────────────────────────────────────────────────────────────────
def create_pareto_waterfall(product_rev: pd.DataFrame, output_path: str, top_n: int = 15) -> None:
    """Create a waterfall chart showing revenue contribution of top products."""
    top = product_rev.head(top_n).copy()
    others_revenue = product_rev.iloc[top_n:]["Revenue"].sum()

    names = top["Product Name"].str[:30].tolist() + ["All Others"]
    values = top["Revenue"].tolist() + [others_revenue]

    measures = ["relative"] * len(names)

    fig = go.Figure(go.Waterfall(
        name="Revenue",
        orientation="v",
        measure=measures,
        x=names,
        y=values,
        textposition="outside",
        text=[f"${v:,.0f}" for v in values],
        connector=dict(line=dict(color="#2a1f47", width=1)),
        increasing=dict(marker=dict(color="#a855f7")),
        decreasing=dict(marker=dict(color="#e040a0")),
        totals=dict(marker=dict(color="#22d3ee")),
    ))

    fig.update_layout(
        title=dict(text=f"<b>Pareto Revenue Waterfall — Top {top_n} Products</b>",
                   font=dict(size=17, color="#f0e8ff")),
        paper_bgcolor="#0a0612",
        plot_bgcolor="#110d1f",
        font=dict(family="Syne, sans-serif", color="#9d8dc0"),
        xaxis=dict(title="Product", gridcolor="#1c1535", tickangle=-40),
        yaxis=dict(title="Incremental Revenue ($)", gridcolor="#1c1535", tickprefix="$"),
        width=1400, height=600,
        showlegend=False,
    )

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    try:
        fig.write_image(output_path)
        logger.info(f"Waterfall chart saved: {output_path}")
    except Exception as e:
        logger.warning(f"Could not save PNG: {e}. Saving HTML fallback.")
        fig.write_html(output_path.replace(".png", ".html"))


# ─────────────────────────────────────────────────────────────────────────────
# 5. Main orchestration function
# ─────────────────────────────────────────────────────────────────────────────
def run_pareto_analysis(cleaned_path: str = "output/cleaned_superstore.csv",
                         output_dir: str = "output") -> dict:
    """Full Pareto analysis pipeline."""
    os.makedirs(output_dir, exist_ok=True)
    logger.info("=" * 60)
    logger.info("Starting Pareto Analysis & KPI Pipeline")
    logger.info("=" * 60)

    logger.info("[Step 1] Loading cleaned data…")
    df = pd.read_csv(cleaned_path)

    logger.info("[Step 2] Pareto — Products…")
    prod = pareto_products(df)
    prod_path = os.path.join(output_dir, "pareto_products.csv")
    prod.to_csv(prod_path, index=False)
    logger.info(f"  → pareto_products.csv saved ({len(prod)} rows)")

    logger.info("[Step 3] Pareto — Regions…")
    reg = pareto_regions(df)
    reg_path = os.path.join(output_dir, "pareto_regions.csv")
    reg.to_csv(reg_path, index=False)
    logger.info(f"  → pareto_regions.csv saved ({len(reg)} rows)")

    logger.info("[Step 4] KPI Metrics…")
    kpi = build_kpi_metrics(df)
    kpi_path = os.path.join(output_dir, "kpi_metrics.csv")
    kpi.to_csv(kpi_path, index=False)
    logger.info(f"  → kpi_metrics.csv saved")

    logger.info("[Step 5] Waterfall chart…")
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

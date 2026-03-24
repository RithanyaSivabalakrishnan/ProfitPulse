"""
Module 5: Anomaly Detection
ProfitPlus — Superstore Sales Analytics Dashboard
"""

import logging
import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# 1. IsolationForest anomaly detection
# ─────────────────────────────────────────────────────────────────────────────
def detect_with_isolation_forest(df: pd.DataFrame,
                                   contamination: float = 0.05,
                                   features: list = None) -> pd.DataFrame:
    """
    Fit IsolationForest on Sales, Profit, Quantity.
    Adds 'IF_Anomaly' (bool) and 'Anomaly_Score' columns.
    """
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler

    if features is None:
        features = ["Sales", "Profit", "Quantity"]

    X = df[features].copy().fillna(0)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    clf = IsolationForest(contamination=contamination, random_state=42, n_estimators=200)
    preds = clf.fit_predict(X_scaled)
    scores = clf.decision_function(X_scaled)   # more negative = more anomalous

    df = df.copy()
    df["IF_Anomaly"] = preds == -1
    df["Anomaly_Score"] = scores.round(6)

    n_anomalies = df["IF_Anomaly"].sum()
    logger.info(
        f"IsolationForest (contamination={contamination}): "
        f"{n_anomalies} anomalies detected ({n_anomalies/len(df)*100:.1f}%)"
    )
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 2. Business rule anomalies
# ─────────────────────────────────────────────────────────────────────────────
def detect_business_rule_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """
    Flag anomalies based on business rules:
    1. Negative profit (loss-making orders)
    2. Impossible ship times (Days to Ship > 30 or < 0)
    3. Zero / negative sales
    4. Discount > 80%
    """
    df = df.copy()
    df["BR_Negative_Profit"] = df["Profit"] < 0
    df["BR_Impossible_Ship"] = False
    if "Days to Ship" in df.columns:
        df["BR_Impossible_Ship"] = (df["Days to Ship"] > 30) | (df["Days to Ship"] < 0)
    df["BR_Zero_Sales"] = df["Sales"] <= 0
    df["BR_High_Discount"] = df.get("Discount", 0) > 0.8

    # Combined business rule flag
    df["BR_Anomaly"] = (
        df["BR_Negative_Profit"] |
        df["BR_Impossible_Ship"] |
        df["BR_Zero_Sales"] |
        df["BR_High_Discount"]
    )

    # Combined anomaly flag (IF or business rule)
    df["Is_Anomaly"] = df["IF_Anomaly"] | df["BR_Anomaly"]

    rules_fired = {
        "Negative Profit": int(df["BR_Negative_Profit"].sum()),
        "Impossible Ship Time": int(df["BR_Impossible_Ship"].sum()),
        "Zero/Negative Sales": int(df["BR_Zero_Sales"].sum()),
        "High Discount (>80%)": int(df["BR_High_Discount"].sum()),
    }
    logger.info(f"Business rule anomalies: {rules_fired}")
    return df, rules_fired


# ─────────────────────────────────────────────────────────────────────────────
# 3. Export top-50 anomalies
# ─────────────────────────────────────────────────────────────────────────────
def export_top_anomalies(df: pd.DataFrame, top_n: int = 50) -> pd.DataFrame:
    """Return top N anomalies sorted by anomaly score (most anomalous first)."""
    anomalies = df[df["Is_Anomaly"]].copy()
    # Sort by most negative anomaly score (IsolationForest convention)
    anomalies = anomalies.sort_values("Anomaly_Score", ascending=True).head(top_n)
    logger.info(f"Top {min(top_n, len(anomalies))} anomalies selected.")
    return anomalies


# ─────────────────────────────────────────────────────────────────────────────
# 4. Plotly scatter chart
# ─────────────────────────────────────────────────────────────────────────────
def create_anomaly_scatter(df: pd.DataFrame, output_path: str) -> None:
    """Create Sales vs Profit scatter, colored by anomaly status."""
    normal = df[~df["Is_Anomaly"]]
    anomalies = df[df["Is_Anomaly"]]

    fig = go.Figure()

    # Normal points
    fig.add_trace(go.Scatter(
        x=normal["Sales"], y=normal["Profit"],
        mode="markers",
        name="Normal",
        marker=dict(color="#a855f7", size=4, opacity=0.5),
        hovertemplate="Sales: $%{x:,.2f}<br>Profit: $%{y:,.2f}<extra>Normal</extra>",
    ))

    # Anomaly points
    fig.add_trace(go.Scatter(
        x=anomalies["Sales"], y=anomalies["Profit"],
        mode="markers",
        name="Anomaly",
        marker=dict(color="#e040a0", size=8, symbol="x", line=dict(width=1.5, color="#ff4dbd")),
        hovertemplate="Sales: $%{x:,.2f}<br>Profit: $%{y:,.2f}<extra>ANOMALY</extra>",
    ))

    # Zero profit threshold line
    fig.add_hline(y=0, line_dash="dash", line_color="#22d3ee", line_width=1,
                   annotation_text="Break-even", annotation_position="top right")

    fig.update_layout(
        title=dict(text="<b>Sales vs Profit — Anomaly Detection</b>", font=dict(size=18, color="#f0e8ff")),
        paper_bgcolor="#0a0612",
        plot_bgcolor="#110d1f",
        font=dict(family="Syne, sans-serif", color="#9d8dc0"),
        xaxis=dict(title="Sales ($)", gridcolor="#1c1535", tickprefix="$"),
        yaxis=dict(title="Profit ($)", gridcolor="#1c1535", tickprefix="$"),
        legend=dict(bgcolor="rgba(17,13,31,0.8)", bordercolor="#2a1f47", borderwidth=1),
        width=1100, height=550,
    )

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    try:
        fig.write_image(output_path)
        logger.info(f"Anomaly scatter saved: {output_path}")
    except Exception as e:
        logger.warning(f"Could not save PNG: {e}. Saving HTML fallback.")
        fig.write_html(output_path.replace(".png", ".html"))


# ─────────────────────────────────────────────────────────────────────────────
# 5. Main orchestration function
# ─────────────────────────────────────────────────────────────────────────────
def run_anomaly_detection(cleaned_path: str = "output/cleaned_superstore.csv",
                           output_dir: str = "output") -> dict:
    """Full anomaly detection pipeline."""
    os.makedirs(output_dir, exist_ok=True)
    logger.info("=" * 60)
    logger.info("Starting Anomaly Detection Pipeline")
    logger.info("=" * 60)

    logger.info("[Step 1] Loading cleaned data…")
    df = pd.read_csv(cleaned_path)
    logger.info(f"  Loaded {len(df):,} rows")

    logger.info("[Step 2] Running IsolationForest…")
    df = detect_with_isolation_forest(df, contamination=0.05)

    logger.info("[Step 3] Applying business rules…")
    df, rules_fired = detect_business_rule_anomalies(df)

    logger.info("[Step 4] Exporting top-50 anomalies…")
    top_anomalies = export_top_anomalies(df, top_n=50)
    anomaly_path = os.path.join(output_dir, "anomalies.csv")
    top_anomalies.to_csv(anomaly_path, index=False)
    logger.info(f"  → anomalies.csv saved ({len(top_anomalies)} rows)")

    logger.info("[Step 5] Creating anomaly scatter chart…")
    scatter_path = os.path.join(output_dir, "anomaly_scatter.png")
    create_anomaly_scatter(df, scatter_path)

    # Summary stats
    total_anomalies = df["Is_Anomaly"].sum()
    pct_anomalous = total_anomalies / len(df) * 100
    avg_impact = df[df["Is_Anomaly"]]["Sales"].mean()

    logger.info("=" * 60)
    logger.info("Anomaly Detection Complete")
    logger.info(f"  Total anomalies: {total_anomalies} ({pct_anomalous:.1f}%)")
    logger.info(f"  Avg revenue impact: ${avg_impact:,.2f}")
    logger.info("=" * 60)

    return {
        "total_anomalies": int(total_anomalies),
        "pct_anomalous": round(pct_anomalous, 2),
        "avg_impact": round(float(avg_impact), 2) if not pd.isna(avg_impact) else 0,
        "business_rules": rules_fired,
        "anomaly_csv": anomaly_path,
        "scatter_path": scatter_path,
    }

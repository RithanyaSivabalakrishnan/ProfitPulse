"""
Module 5: Anomaly Detection
ProfitPlus — Superstore Sales Analytics Dashboard
Column names: sales, profit, quantity, order_id, days_to_ship, discount
"""

import logging
import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go

logger = logging.getLogger(__name__)


def detect_with_isolation_forest(df: pd.DataFrame,
                                   contamination: float = 0.05,
                                   features: list = None) -> pd.DataFrame:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler

    if features is None:
        features = [c for c in ["sales", "profit", "quantity"] if c in df.columns]

    X = df[features].copy().fillna(0)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    clf = IsolationForest(contamination=contamination, random_state=42, n_estimators=200)
    preds = clf.fit_predict(X_scaled)
    scores = clf.decision_function(X_scaled)

    df = df.copy()
    df["IF_Anomaly"] = preds == -1
    df["Anomaly_Score"] = scores.round(6)

    n = df["IF_Anomaly"].sum()
    logger.info(f"IsolationForest: {n} anomalies ({n/len(df)*100:.1f}%)")
    return df


def detect_business_rule_anomalies(df: pd.DataFrame) -> tuple:
    df = df.copy()
    df["BR_Negative_Profit"] = df["profit"] < 0
    df["BR_Impossible_Ship"] = False
    if "days_to_ship" in df.columns:
        df["BR_Impossible_Ship"] = (df["days_to_ship"] > 30) | (df["days_to_ship"] < 0)
    df["BR_Zero_Sales"] = df["sales"] <= 0
    df["BR_High_Discount"] = df.get("discount", 0) > 0.8

    df["BR_Anomaly"] = (
        df["BR_Negative_Profit"] | df["BR_Impossible_Ship"] |
        df["BR_Zero_Sales"] | df["BR_High_Discount"]
    )
    df["Is_Anomaly"] = df["IF_Anomaly"] | df["BR_Anomaly"]

    rules_fired = {
        "Negative Profit": int(df["BR_Negative_Profit"].sum()),
        "Impossible Ship Time": int(df["BR_Impossible_Ship"].sum()),
        "Zero/Negative Sales": int(df["BR_Zero_Sales"].sum()),
        "High Discount (>80%)": int(df["BR_High_Discount"].sum()),
    }
    logger.info(f"Business rule anomalies: {rules_fired}")
    return df, rules_fired


def export_top_anomalies(df: pd.DataFrame, top_n: int = 50) -> pd.DataFrame:
    anomalies = df[df["Is_Anomaly"]].copy()
    anomalies = anomalies.sort_values("Anomaly_Score", ascending=True).head(top_n)
    logger.info(f"Top {min(top_n, len(anomalies))} anomalies selected.")
    return anomalies


def create_anomaly_scatter(df: pd.DataFrame, output_path: str) -> None:
    normal = df[~df["Is_Anomaly"]]
    anomalies = df[df["Is_Anomaly"]]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=normal["sales"], y=normal["profit"],
        mode="markers", name="Normal",
        marker=dict(color="#a855f7", size=4, opacity=0.5),
    ))
    fig.add_trace(go.Scatter(
        x=anomalies["sales"], y=anomalies["profit"],
        mode="markers", name="Anomaly",
        marker=dict(color="#e040a0", size=8, symbol="x", line=dict(width=1.5, color="#ff4dbd")),
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="#22d3ee", line_width=1,
                   annotation_text="Break-even", annotation_position="top right")

    fig.update_layout(
        title=dict(text="<b>Sales vs Profit — Anomaly Detection</b>", font=dict(size=18, color="#f0e8ff")),
        paper_bgcolor="#0a0612", plot_bgcolor="#110d1f",
        font=dict(color="#9d8dc0"),
        xaxis=dict(title="Sales ($)", gridcolor="#1c1535", tickprefix="$"),
        yaxis=dict(title="Profit ($)", gridcolor="#1c1535", tickprefix="$"),
        width=1100, height=550,
    )

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    try:
        fig.write_image(output_path)
        logger.info(f"Scatter saved: {output_path}")
    except Exception as e:
        logger.warning(f"PNG save failed ({e}), saving HTML fallback.")
        fig.write_html(output_path.replace(".png", ".html"))


def run_anomaly_detection(cleaned_path: str = "output/cleaned_superstore.csv",
                           output_dir: str = "output") -> dict:
    os.makedirs(output_dir, exist_ok=True)
    logger.info("=" * 60)
    logger.info("Starting Anomaly Detection Pipeline")
    logger.info("=" * 60)

    df = pd.read_csv(cleaned_path)
    logger.info(f"Loaded {len(df):,} rows")

    df = detect_with_isolation_forest(df, contamination=0.05)
    df, rules_fired = detect_business_rule_anomalies(df)

    top_anomalies = export_top_anomalies(df, top_n=50)
    anomaly_path = os.path.join(output_dir, "anomalies.csv")
    top_anomalies.to_csv(anomaly_path, index=False)

    scatter_path = os.path.join(output_dir, "anomaly_scatter.png")
    create_anomaly_scatter(df, scatter_path)

    total = df["Is_Anomaly"].sum()
    pct = total / len(df) * 100
    avg_impact = df[df["Is_Anomaly"]]["sales"].mean()

    logger.info("=" * 60)
    logger.info(f"Anomaly Detection Complete — {total} anomalies ({pct:.1f}%)")
    logger.info("=" * 60)

    return {
        "total_anomalies": int(total),
        "pct_anomalous": round(pct, 2),
        "avg_impact": round(float(avg_impact), 2) if not pd.isna(avg_impact) else 0,
        "business_rules": rules_fired,
        "anomaly_csv": anomaly_path,
        "scatter_path": scatter_path,
    }

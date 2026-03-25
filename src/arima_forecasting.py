"""
Module 4: ARIMA Time Series Forecasting
ProfitPlus — Superstore Sales Analytics Dashboard
"""

import logging
import os
import warnings
import numpy as np
import pandas as pd
import plotly.graph_objects as go

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Load and prepare monthly sales series
# ─────────────────────────────────────────────────────────────────────────────
def load_monthly_sales(filepath: str) -> pd.Series:
    """Load monthly_sales.csv and return a pd.Series indexed by datetime."""
    df = pd.read_csv(filepath)
    # Support both 'YearMonth' and 'year_month' column names
    date_col = "YearMonth" if "YearMonth" in df.columns else df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col].astype(str).str[:7], format="%Y-%m")
    df = df.set_index(date_col).sort_index()
    value_col = "Sales" if "Sales" in df.columns else "sales"
    series = df[value_col].dropna()
    logger.info(f"Loaded monthly sales: {len(series)} periods ({series.index[0].date()} to {series.index[-1].date()})")
    return series


# ─────────────────────────────────────────────────────────────────────────────
# 2. Fit ARIMA model
# ─────────────────────────────────────────────────────────────────────────────
def fit_arima(series: pd.Series, order: tuple = (2, 1, 2)) -> object:
    """
    Fit ARIMA model. Tries specified order first, falls back to auto_arima.
    Returns the fitted model result.
    """
    from statsmodels.tsa.arima.model import ARIMA

    # Train / validation split (last 3 months as hold-out)
    train = series.iloc[:-3]
    val = series.iloc[-3:]

    logger.info(f"Fitting ARIMA{order} on {len(train)} training periods…")

    try:
        model = ARIMA(train, order=order)
        result = model.fit()
        logger.info(f"ARIMA{order} fitted. AIC={result.aic:.2f}, BIC={result.bic:.2f}")
    except Exception as e:
        logger.warning(f"ARIMA{order} failed ({e}). Attempting auto_arima fallback…")
        try:
            from pmdarima import auto_arima
            auto_result = auto_arima(
                train,
                start_p=0, start_q=0,
                max_p=4, max_q=4,
                d=1, seasonal=False,
                stepwise=True, suppress_warnings=True,
                error_action="ignore",
            )
            logger.info(f"auto_arima selected order: {auto_result.order}")
            model = ARIMA(train, order=auto_result.order)
            result = model.fit()
        except Exception as e2:
            logger.error(f"auto_arima also failed: {e2}. Falling back to ARIMA(1,1,1).")
            model = ARIMA(train, order=(1, 1, 1))
            result = model.fit()

    # ── Validation RMSE ──────────────────────────────────────────────────────
    forecast_val = result.forecast(steps=3)
    rmse = np.sqrt(np.mean((val.values - forecast_val.values) ** 2))
    logger.info(f"Validation RMSE (3 months): ${rmse:,.2f}")

    return result, rmse, train, val


# ─────────────────────────────────────────────────────────────────────────────
# 3. Generate 3-month forecast
# ─────────────────────────────────────────────────────────────────────────────
def generate_forecast(result, series: pd.Series, steps: int = 3) -> pd.DataFrame:
    """Generate forecast with 95% confidence intervals."""
    forecast_result = result.get_forecast(steps=steps)
    forecast_mean = forecast_result.predicted_mean
    conf_int = forecast_result.conf_int(alpha=0.05)

    # Build future dates
    last_date = series.index[-1]
    future_dates = pd.date_range(start=last_date + pd.DateOffset(months=1),
                                  periods=steps, freq="MS")

    forecast_df = pd.DataFrame({
        "YearMonth": future_dates,
        "Sales": np.nan,
        "Forecast": forecast_mean.values,
        "Lower_CI": conf_int.iloc[:, 0].values,
        "Upper_CI": conf_int.iloc[:, 1].values,
        "Is_Forecast": True,
    })

    # Combine historical + forecast
    historical = series.reset_index().rename(columns={"index": "YearMonth", 0: "Sales"})
    historical.columns = ["YearMonth", "Sales"]
    historical["Forecast"] = np.nan
    historical["Lower_CI"] = np.nan
    historical["Upper_CI"] = np.nan
    historical["Is_Forecast"] = False

    combined = pd.concat([historical, forecast_df], ignore_index=True)
    logger.info(f"Forecast generated for {future_dates[0].date()} to {future_dates[-1].date()}")
    return combined


# ─────────────────────────────────────────────────────────────────────────────
# 4. Diagnostics: Ljung-Box test
# ─────────────────────────────────────────────────────────────────────────────
def run_diagnostics(result) -> dict:
    """Run Ljung-Box test on residuals and return diagnostic dict."""
    from statsmodels.stats.diagnostic import acorr_ljungbox
    lb_result = acorr_ljungbox(result.resid, lags=[10], return_df=True)
    lb_stat = float(lb_result["lb_stat"].iloc[0])
    lb_p = float(lb_result["lb_pvalue"].iloc[0])
    white_noise = lb_p > 0.05
    logger.info(f"Ljung-Box test (lag=10): stat={lb_stat:.4f}, p={lb_p:.4f} → {'White noise ✓' if white_noise else 'Autocorrelation remains ✗'}")
    return {
        "ljung_box_stat": round(lb_stat, 4),
        "ljung_box_p": round(lb_p, 4),
        "residuals_white_noise": white_noise,
        "aic": round(result.aic, 2),
        "bic": round(result.bic, 2),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. Plotly chart
# ─────────────────────────────────────────────────────────────────────────────
def create_forecast_chart(combined: pd.DataFrame, output_path: str) -> None:
    """Create a Plotly line chart with historical + forecast + CI bands."""
    hist = combined[~combined["Is_Forecast"]]
    fore = combined[combined["Is_Forecast"]]

    fig = go.Figure()

    # Historical sales
    fig.add_trace(go.Scatter(
        x=hist["YearMonth"], y=hist["Sales"],
        mode="lines+markers",
        name="Historical Sales",
        line=dict(color="#a855f7", width=2.5),
        marker=dict(size=5),
    ))

    # 95% CI band
    fig.add_trace(go.Scatter(
        x=pd.concat([fore["YearMonth"], fore["YearMonth"].iloc[::-1]]),
        y=pd.concat([fore["Upper_CI"], fore["Lower_CI"].iloc[::-1]]),
        fill="toself",
        fillcolor="rgba(224,64,160,0.15)",
        line=dict(color="rgba(255,255,255,0)"),
        name="95% Confidence Interval",
        showlegend=True,
    ))

    # Forecast line
    fig.add_trace(go.Scatter(
        x=fore["YearMonth"], y=fore["Forecast"],
        mode="lines+markers",
        name="ARIMA Forecast",
        line=dict(color="#e040a0", width=3, dash="dash"),
        marker=dict(size=8, symbol="diamond"),
    ))

    fig.update_layout(
        title=dict(text="<b>Monthly Sales — ARIMA Forecast</b>", font=dict(size=18, color="#f0e8ff")),
        paper_bgcolor="#0a0612",
        plot_bgcolor="#110d1f",
        font=dict(family="Syne, sans-serif", color="#9d8dc0"),
        xaxis=dict(title="Month", gridcolor="#1c1535", showgrid=True),
        yaxis=dict(title="Sales ($)", gridcolor="#1c1535", showgrid=True, tickprefix="$"),
        legend=dict(bgcolor="rgba(17,13,31,0.8)", bordercolor="#2a1f47", borderwidth=1),
        hovermode="x unified",
        width=1200, height=500,
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    try:
        fig.write_image(output_path)
        logger.info(f"Chart saved: {output_path}")
    except Exception as e:
        logger.warning(f"Could not save PNG (kaleido may not be installed): {e}")
        # Save as HTML fallback
        html_path = output_path.replace(".png", ".html")
        fig.write_html(html_path)
        logger.info(f"Chart saved as HTML fallback: {html_path}")


# ─────────────────────────────────────────────────────────────────────────────
# 6. Main orchestration function
# ─────────────────────────────────────────────────────────────────────────────
def run_arima_forecast(monthly_sales_path: str = "output/monthly_sales.csv",
                        output_dir: str = "output") -> dict:
    """
    Full ARIMA forecasting pipeline.
    Returns dict with model metrics and file paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    logger.info("=" * 60)
    logger.info("Starting ARIMA Forecasting Pipeline")
    logger.info("=" * 60)

    logger.info("[Step 1] Loading monthly sales…")
    series = load_monthly_sales(monthly_sales_path)

    logger.info("[Step 2] Fitting ARIMA model…")
    result, rmse, train, val = fit_arima(series, order=(2, 1, 2))

    logger.info("[Step 3] Generating 3-month forecast…")
    combined = generate_forecast(result, series, steps=3)

    combined_path = os.path.join(output_dir, "monthly_sales_arima.csv")
    combined.to_csv(combined_path, index=False)
    logger.info(f"  → monthly_sales_arima.csv saved")

    logger.info("[Step 4] Running diagnostics…")
    diagnostics = run_diagnostics(result)
    diagnostics["validation_rmse"] = round(rmse, 2)
    diagnostics["validation_rmse_pct"] = round(rmse / val.mean() * 100, 2)

    logger.info("[Step 5] Creating forecast chart…")
    chart_path = os.path.join(output_dir, "arima_forecast.png")
    create_forecast_chart(combined, chart_path)

    logger.info("=" * 60)
    logger.info("ARIMA Forecasting Complete")
    logger.info(f"  RMSE: ${diagnostics['validation_rmse']:,.2f} ({diagnostics['validation_rmse_pct']:.1f}%)")
    logger.info("=" * 60)

    return {
        "diagnostics": diagnostics,
        "combined_df": combined,
        "forecast_csv": combined_path,
        "chart_path": chart_path,
    }

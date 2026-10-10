import duckdb
import pandas as pd
import numpy as np
from statsmodels.tsa.holtwinters import ExponentialSmoothing
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PROC, parquet  # noqa: E402

def run_forecasting():
    conn = duckdb.connect()
    df_sales = conn.read_parquet(parquet('fact_sales')).df()
    conn.close()

    # Aggregate to weekly revenue
    df_sales['week_start'] = pd.to_datetime(df_sales['invoice_ts']).dt.to_period('W').dt.start_time
    df_weekly = df_sales.groupby('week_start')['net_revenue_line'].sum().reset_index()
    df_weekly.columns = ['week_start', 'actual']
    df_weekly = df_weekly.sort_values('week_start').reset_index(drop=True)

    # Drop partial boundary weeks
    df_weekly = df_weekly.iloc[1:-1].reset_index(drop=True)

    # 80/20 Chronological Split
    split_idx = int(len(df_weekly) * 0.8)
    train = df_weekly.iloc[:split_idx].copy()
    test = df_weekly.iloc[split_idx:].copy()

    # Baseline 1: Naive (last observed value)
    naive_val = train['actual'].iloc[-1]
    test['naive'] = naive_val

    # Holt-Winters Model
    model = ExponentialSmoothing(train['actual'], trend='add', seasonal=None).fit()
    test['forecast'] = model.forecast(len(test)).values

    # Evaluation Metrics
    mae_naive = np.mean(np.abs(test['actual'] - test['naive']))
    mae_model = np.mean(np.abs(test['actual'] - test['forecast']))
    mape_model = np.mean(np.abs((test['actual'] - test['forecast']) / test['actual'])) * 100

    print(f"✅ Forecasting Complete:")
    print(f"   Naive Baseline MAE:  £{mae_naive:,.2f}")
    print(f"   Holt-Winters MAE:    £{mae_model:,.2f}")
    print(f"   Holt-Winters MAPE:   {mape_model:.2f}%")

    # Flag splits and save output
    train['split'] = 'train'
    test['split'] = 'test'
    train['naive'] = np.nan
    train['forecast'] = np.nan

    df_out = pd.concat([train, test], ignore_index=True)
    os.makedirs(PROC, exist_ok=True)
    df_out.to_parquet(parquet('forecast_weekly'))

    metrics_df = pd.DataFrame([{
        'mae_naive': mae_naive,
        'mae_model': mae_model,
        'mape_model': mape_model
    }])
    metrics_df.to_parquet(parquet('forecast_metrics'))

if __name__ == "__main__":
    run_forecasting()
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import parquet  # noqa: E402
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Forecast | RetailPulse AI", layout="wide")
st.title("🔮 Weekly Net Revenue Forecast")


@st.cache_data
def load_forecast():
    return pd.read_parquet(parquet('forecast_weekly')), pd.read_parquet(parquet('forecast_metrics'))


try:
    weekly, metrics = load_forecast()
except OSError:
    st.warning("Forecast files not found. Run: python run.py forecast")
    st.stop()

best = metrics[metrics['is_best']].iloc[0]
hw = metrics[metrics['model'] == 'holt_winters'].iloc[0]
col1, col2, col3 = st.columns(3)
col1.metric("Best model (lowest holdout MAE)", best['model'])
col2.metric("Best model MAE", f"£{best['mae']:,.0f}")
col3.metric("Holt-Winters MAE vs naive", f"{hw['improvement_mae_pct_vs_naive']:+.1f}%")

if hw['beats_naive']:
    st.success("Holt-Winters beats the naive baseline on the holdout.")
else:
    st.warning("Holt-Winters does not beat the naive baseline on the holdout. "
               f"The best model is {best['model']}. Results are reported as measured.")

weekly['week_start'] = pd.to_datetime(weekly['week_start'])
fig = go.Figure()
fig.add_scatter(x=weekly['week_start'], y=weekly['actual'], name='Actual', mode='lines')
fut = weekly[weekly['split'].isin(['test', 'future'])]
fig.add_scatter(x=fut['week_start'], y=fut['forecast'], name='Holt-Winters forecast', mode='lines')
fig.add_scatter(x=fut['week_start'], y=fut['seasonal_naive_52w'], name='Seasonal naive (52 weeks)', mode='lines')
test = weekly[weekly['split'] == 'test']
fig.add_scatter(x=test['week_start'], y=test['naive'], name='Naive (last value)', mode='lines')
band = fut.dropna(subset=['lower', 'upper'])
fig.add_scatter(x=pd.concat([band['week_start'], band['week_start'][::-1]]),
                y=pd.concat([band['upper'], band['lower'][::-1]]),
                fill='toself', name='Holt-Winters interval', line={'width': 0}, opacity=0.2)
fig.update_layout(yaxis_title='Net revenue (£)', xaxis_title='Week')
st.plotly_chart(fig, width='stretch')

st.subheader("Holdout metrics")
st.dataframe(metrics[['model', 'mae', 'mape', 'wape', 'improvement_mae_pct_vs_naive', 'beats_naive', 'is_best']],
             width='stretch')
st.caption("Chronological 80/20 split on complete weeks. MAPE excludes zero-revenue weeks. "
           "With about two years of history, Holt-Winters cannot learn yearly seasonality.")

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import parquet  # noqa: E402
import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Executive Overview | RetailPulse AI", layout="wide")
st.title("📈 Executive Overview")

@st.cache_data
def load_data():
    conn = duckdb.connect()
    df_monthly = conn.read_parquet(parquet('mart_monthly_sales')).df()
    conn.close()
    return df_monthly

df = load_data()

# Global KPI summary
total_net_rev = df['net_revenue'].sum()
total_orders = df['order_count'].sum()
avg_aov = df['gross_sales'].sum() / total_orders if total_orders > 0 else 0

col1, col2, col3 = st.columns(3)
col1.metric("Total Net Revenue", f"£{total_net_rev:,.2f}")
col2.metric("Total Orders", f"{total_orders:,}")
col3.metric("Average Order Value (AOV)", f"£{avg_aov:,.2f}")

st.divider()

# Monthly Revenue Trend
st.subheader("Monthly Net Revenue Trend")
df_trend = df.groupby('sales_month', as_index=False)['net_revenue'].sum().sort_values('sales_month')
fig_trend = px.line(df_trend, x='sales_month', y='net_revenue', markers=True, labels={'sales_month': 'Month', 'net_revenue': 'Net Revenue (£)'})
st.plotly_chart(fig_trend, width='stretch')

# Geographic Breakdown
st.subheader("Top Countries by Net Revenue")
df_geo = df.groupby('country', as_index=False)['net_revenue'].sum().sort_values('net_revenue', ascending=False).head(10)
fig_geo = px.bar(df_geo, x='net_revenue', y='country', orientation='h', labels={'net_revenue': 'Net Revenue (£)', 'country': 'Country'})
fig_geo.update_layout(yaxis={'categoryorder': 'total ascending'})
st.plotly_chart(fig_geo, width='stretch')
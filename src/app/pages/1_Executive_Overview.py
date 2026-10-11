import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import parquet  # noqa: E402
from kpis import format_kpi, store_kpis  # noqa: E402
import streamlit as st
import duckdb
import plotly.express as px

st.set_page_config(page_title="Executive Overview | RetailPulse AI", layout="wide")
st.title("📈 Executive Overview")


@st.cache_data
def load_data():
    conn = duckdb.connect()
    df_monthly = conn.read_parquet(parquet('mart_monthly_sales')).df()
    conn.close()
    return df_monthly


@st.cache_data
def load_kpis():
    return store_kpis()


df = load_data()

# KPI cards use the metrics contract (same definitions as Power BI and the tests).
kpis = load_kpis()
for row in (kpis[:3], kpis[3:]):
    cols = st.columns(len(row))
    for col, k in zip(cols, row):
        col.metric(k['label'], format_kpi(k['name'], k['value']))

partial = df[df['is_partial_month']]['sales_month']
if len(partial):
    st.caption(f"Totals include the partial final month ({partial.max():%b %Y}); it is excluded from growth comparisons.")

st.divider()

# Monthly Revenue Trend
st.subheader("Monthly Net Revenue Trend")
df_trend = df.groupby('sales_month', as_index=False)['net_revenue'].sum().sort_values('sales_month')
fig_trend = px.line(df_trend, x='sales_month', y='net_revenue', markers=True,
                    labels={'sales_month': 'Month', 'net_revenue': 'Net Revenue (£)'})
st.plotly_chart(fig_trend, width='stretch')

# Geographic Breakdown
st.subheader("Top Countries by Net Revenue")
df_geo = df.groupby('country', as_index=False)['net_revenue'].sum().sort_values('net_revenue', ascending=False).head(10)
fig_geo = px.bar(df_geo, x='net_revenue', y='country', orientation='h',
                 labels={'net_revenue': 'Net Revenue (£)', 'country': 'Country'})
fig_geo.update_layout(yaxis={'categoryorder': 'total ascending'})
st.plotly_chart(fig_geo, width='stretch')

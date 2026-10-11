import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import parquet  # noqa: E402
import streamlit as st
import duckdb
import plotly.express as px

st.set_page_config(page_title="Product Performance | RetailPulse AI", layout="wide")
st.title("📦 Product Performance & Pareto Analysis")

@st.cache_data
def load_products():
    conn = duckdb.connect()
    df_prod = conn.read_parquet(parquet('mart_product_performance')).df()
    conn.close()
    return df_prod

df_prod = load_products()

total_products = len(df_prod)
ranked_products = int(df_prod['pareto_rank'].notna().sum())  # products with positive net revenue
top_80_count = int(df_prod['is_top_80'].sum())
pct_top = (top_80_count / ranked_products) * 100 if ranked_products > 0 else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Products", f"{total_products:,}")
col2.metric("Ranked Products (positive revenue)", f"{ranked_products:,}")
col3.metric("Top 80% Revenue Products", f"{top_80_count:,}")
col4.metric("Pareto Density (% of ranked SKUs)", f"{pct_top:.2f}%")

st.divider()

st.subheader("Pareto Distribution (Cumulative Revenue Share)")
fig_pareto = px.line(df_prod.dropna(subset=['pareto_rank']), x='pareto_rank', y='cumulative_share',
                     labels={'pareto_rank': 'Product Rank', 'cumulative_share': 'Cumulative Revenue Share'})
fig_pareto.add_hline(y=0.8, line_dash="dash", line_color="red", annotation_text="80% Threshold")
st.plotly_chart(fig_pareto, width='stretch')

st.subheader("Top Products Table")
top_table = df_prod.sort_values('net_revenue', ascending=False)
st.dataframe(top_table[['stock_code', 'description', 'net_revenue', 'units_sold', 'return_rate', 'is_top_80']].head(50), width='stretch')
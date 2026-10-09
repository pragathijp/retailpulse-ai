import streamlit as st
import duckdb
import plotly.express as px

st.set_page_config(page_title="Product Performance | RetailPulse AI", layout="wide")
st.title("📦 Product Performance & Pareto Analysis")

@st.cache_data
def load_products():
    conn = duckdb.connect()
    df_prod = conn.read_parquet("data/processed/mart_product_performance.parquet").df()
    conn.close()
    return df_prod

df_prod = load_products()

top_80_count = df_prod['is_top_80'].sum()
total_products = len(df_prod)
pct_top = (top_80_count / total_products) * 100 if total_products > 0 else 0

col1, col2, col3 = st.columns(3)
col1.metric("Total Products", f"{total_products:,}")
col2.metric("Top 80% Revenue Products", f"{top_80_count:,}")
col3.metric("Pareto Density (% of SKUs)", f"{pct_top:.1f}%")

st.divider()

st.subheader("Pareto Distribution (Cumulative Revenue Share)")
fig_pareto = px.line(df_prod.dropna(subset=['pareto_rank']), x='pareto_rank', y='cumulative_share',
                     labels={'pareto_rank': 'Product Rank', 'cumulative_share': 'Cumulative Revenue Share'})
fig_pareto.add_hline(y=0.8, line_dash="dash", line_color="red", annotation_text="80% Threshold")
st.plotly_chart(fig_pareto, use_container_width=True)

st.subheader("Top Products Table")
st.dataframe(df_prod[['stock_code', 'description', 'net_revenue', 'units_sold', 'return_rate', 'is_top_80']].head(50), use_container_width=True)
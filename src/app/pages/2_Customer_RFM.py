import streamlit as st
import duckdb
import plotly.express as px

st.set_page_config(page_title="Customer RFM | RetailPulse AI", layout="wide")
st.title("👥 Customer RFM Segmentation")

@st.cache_data
def load_rfm():
    conn = duckdb.connect()
    df_rfm = conn.read_parquet("data/processed/mart_customer_rfm.parquet").df()
    conn.close()
    return df_rfm

df_rfm = load_rfm()

col1, col2 = st.columns(2)
col1.metric("Total Tracked Customers", f"{len(df_rfm):,}")
col2.metric("Total Customer Revenue", f"£{df_rfm['monetary'].sum():,.2f}")

st.divider()

# Segment Distribution Chart
st.subheader("Customer Distribution by Segment")
df_seg = df_rfm.groupby('segment', as_index=False).agg(
    customer_count=('customer_id', 'count'),
    total_monetary=('monetary', 'sum')
).sort_values('total_monetary', ascending=False)

fig_seg = px.bar(df_seg, x='segment', y='customer_count', color='total_monetary',
                 labels={'segment': 'RFM Segment', 'customer_count': 'Customer Count', 'total_monetary': 'Total Revenue (£)'})
st.plotly_chart(fig_seg, use_container_width=True)

st.subheader("RFM Segment Details")
st.dataframe(df_seg, use_container_width=True)
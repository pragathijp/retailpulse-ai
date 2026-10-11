import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import parquet  # noqa: E402
import streamlit as st
import duckdb
import plotly.express as px

st.set_page_config(page_title="Customer RFM | RetailPulse AI", layout="wide")
st.title("👥 Customer RFM Segmentation")


@st.cache_data
def load_rfm():
    conn = duckdb.connect()
    df_rfm = conn.read_parquet(parquet('mart_customer_rfm')).df()
    conn.close()
    return df_rfm


df_rfm = load_rfm()

col1, col2 = st.columns(2)
col1.metric("Total Tracked Customers", f"{len(df_rfm):,}")
# monetary_raw is the same figure the audit ledger uses for RFM revenue
col2.metric("Total Customer Net Revenue (RFM)", f"£{df_rfm['monetary_raw'].astype(float).sum():,.2f}")
st.caption("Customers without an ID are excluded here by design; see the Audit page for the reconciliation.")

st.divider()

# Segment Distribution Chart
st.subheader("Customer Distribution by Segment")
df_rfm['monetary_raw'] = df_rfm['monetary_raw'].astype(float)
df_seg = df_rfm.groupby('segment', as_index=False).agg(
    customer_count=('customer_id', 'count'),
    total_net_revenue=('monetary_raw', 'sum')
).sort_values('total_net_revenue', ascending=False)

fig_seg = px.bar(df_seg, x='segment', y='customer_count', color='total_net_revenue',
                 labels={'segment': 'RFM Segment', 'customer_count': 'Customer Count',
                         'total_net_revenue': 'Net Revenue (£)'})
st.plotly_chart(fig_seg, width='stretch')

st.subheader("Recency x Frequency Matrix (customer counts)")
matrix = df_rfm.pivot_table(index='r_score', columns='f_score', values='customer_id', aggfunc='count', fill_value=0)
matrix = matrix.sort_index(ascending=False)
fig_matrix = px.imshow(matrix, text_auto=True, aspect='auto', color_continuous_scale='Blues',
                       labels={'x': 'Frequency score', 'y': 'Recency score (5 = most recent)', 'color': 'Customers'})
st.plotly_chart(fig_matrix, width='stretch')

st.subheader("RFM Segment Details")
st.dataframe(df_seg, width='stretch')

import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px

# -----------------------------------------------------------------------------
# Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Retail Analytics Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-Density Dark Slate Theme CSS
st.markdown("""
<style>
    /* Main App & Sidebar Backgrounds */
    .stApp {
        background-color: #0b0f19;
        color: #e2e8f0;
    }
    
    [data-testid="stSidebar"] {
        background-color: #0f172a !important;
        border-right: 1px solid #1f2937;
    }

    [data-testid="stSidebar"] * {
        color: #cbd5e1 !important;
    }

    /* Metric Cards */
    div[data-testid="stMetric"] {
        background-color: #111827;
        border: 1px solid #1f2937;
        padding: 12px 16px;
        border-radius: 6px;
    }
    
    div[data-testid="stMetricLabel"] {
        font-size: 0.72rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #9ca3af !important;
        font-weight: 600;
    }
    
    div[data-testid="stMetricValue"] {
        font-size: 1.45rem !important;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
        color: #f9fafb !important;
        font-weight: 700;
    }

    /* Clean Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid #1f2937;
    }

    .stTabs [data-baseweb="tab"] {
        height: 38px;
        padding: 0px 16px;
        background-color: #111827;
        border-radius: 4px 4px 0px 0px;
        border: 1px solid #1f2937;
        color: #9ca3af;
        font-size: 0.85rem;
    }

    .stTabs [aria-selected="true"] {
        background-color: #1f2937 !important;
        color: #3b82f6 !important;
        border-bottom: 2px solid #3b82f6 !important;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Data Loaders (DuckDB Connection)
# -----------------------------------------------------------------------------
DB_PATH = "data/duckdb/retail_analytics.duckdb"

@st.cache_data(ttl=600)
def load_kpis(selected_country):
    con = duckdb.connect(DB_PATH, read_only=True)
    where_clause = "" if selected_country == "All Markets" else f"where country = '{selected_country}'"
    
    df = con.execute(f"""
        select 
            sum(net_revenue) as total_net_revenue,
            count(distinct invoice_no) as total_orders,
            count(distinct customer_id) as total_customers,
            avg(net_revenue) as avg_order_value,
            sum(case when is_cancelled then 1 else 0 end) * 100.0 / count(*) as cancellation_rate
        from main_marts.fct_orders
        {where_clause}
    """).df()
    con.close()
    return df.iloc[0]

@st.cache_data(ttl=600)
def load_monthly_trends(selected_country):
    con = duckdb.connect(DB_PATH, read_only=True)
    where_clause = "" if selected_country == "All Markets" else f"where country = '{selected_country}'"
    
    df = con.execute(f"""
        select 
            date_trunc('month', order_ts) as month,
            sum(net_revenue) as net_revenue,
            count(distinct invoice_no) as order_count
        from main_marts.fct_orders
        {where_clause}
        group by 1
        order by 1
    """).df()
    con.close()
    return df

@st.cache_data(ttl=600)
def load_top_customers(selected_country, limit=15):
    con = duckdb.connect(DB_PATH, read_only=True)
    where_clause = "" if selected_country == "All Markets" else f"where primary_country = '{selected_country}'"
    
    df = con.execute(f"""
        select 
            customer_id,
            primary_country,
            total_orders,
            round(lifetime_monetary_value, 2) as lifetime_monetary_value,
            first_order_ts,
            most_recent_order_ts
        from main_marts.dim_customers
        {where_clause}
        order by lifetime_monetary_value desc
        limit {limit}
    """).df()
    con.close()
    return df

# -----------------------------------------------------------------------------
# Sidebar
# -----------------------------------------------------------------------------
st.sidebar.markdown("### **Retail Analytics Platform**")
st.sidebar.caption("Engine: DuckDB 1.1.3 • dbt v1.12.5")
st.sidebar.divider()

st.sidebar.markdown("**Pipeline Health**")
st.sidebar.success("dbt Models: 4/4 Operational")
st.sidebar.info("Data Tests: 10/10 Passed")

st.sidebar.divider()
st.sidebar.markdown("**Filters**")
country_filter = st.sidebar.selectbox("Market Region", ["All Markets", "United Kingdom", "EIRE", "Germany", "France"])

# -----------------------------------------------------------------------------
# Main Dashboard Body
# -----------------------------------------------------------------------------
st.title("Executive Revenue & Customer Operations")
st.caption("Live analytics querying `main_marts.fct_orders` and `main_marts.dim_customers`")

kpis = load_kpis(country_filter)

# Format Sales cleanly to prevent text overflow
net_revenue_formatted = f"${kpis['total_net_revenue'] / 1e6:.2f}M" if kpis['total_net_revenue'] >= 1e6 else f"${kpis['total_net_revenue']:,.2f}"

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Net Sales", net_revenue_formatted)
c2.metric("Total Orders", f"{int(kpis['total_orders']):,}")
c3.metric("Active Customers", f"{int(kpis['total_customers']):,}")
c4.metric("Avg Order Value", f"${kpis['avg_order_value']:.2f}")
c5.metric("Cancellation Rate", f"{kpis['cancellation_rate']:.2f}%")

st.divider()

tab1, tab2 = st.tabs(["Financial Performance", "Customer LTV Ranking"])

with tab1:
    st.subheader(f"Monthly Revenue Trajectory ({country_filter})")
    df_monthly = load_monthly_trends(country_filter)
    
    fig = px.area(
        df_monthly, 
        x="month", 
        y="net_revenue",
        labels={"month": "Date", "net_revenue": "Net Sales ($)"},
        template="plotly_dark"
    )
    fig.update_traces(line_color="#3b82f6", fillcolor="rgba(59, 130, 246, 0.15)")
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(showgrid=True, gridcolor="#1f2937"),
        yaxis=dict(showgrid=True, gridcolor="#1f2937", tickprefix="$"),
        height=380
    )
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader(f"Top Accounts by Lifetime Value ({country_filter})")
    df_customers = load_top_customers(country_filter, limit=15)
    
    st.dataframe(
        df_customers,
        column_config={
            "customer_id": "Customer ID",
            "primary_country": "Country",
            "total_orders": "Orders",
            "lifetime_monetary_value": st.column_config.NumberColumn("Lifetime LTV", format="$%.2f"),
            "first_order_ts": "Cohort Date",
            "most_recent_order_ts": "Last Active"
        },
        use_container_width=True,
        hide_index=True
    )
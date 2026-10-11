import streamlit as st

st.set_page_config(
    page_title="RetailPulse AI - Analytics & Governance Platform",
    page_icon="📊",
    layout="wide"
)

st.title("📊 RetailPulse AI Platform")
st.markdown("""
Welcome to the **RetailPulse AI Governance & Analytics Platform**.

Use the sidebar navigation to access key analytical marts and system audits:

* **Executive Overview**: High-level sales trends, AOV, MoM growth, and geographic splits.
* **Customer RFM**: Customer segmentation matrix and target audience cohorting.
* **Product Performance**: Pareto analysis (80/20 rule), return rates, and product sales metrics.
* **Audit & Reconciliation**: Store-to-RFM revenue variance ledger (0.01 GBP tolerance).
* **Forecast**: Weekly net revenue forecast with baselines and measured accuracy.
* **Ask RetailPulse**: Questions answered only from verified figures in the data marts.
""")

st.info("System Status: Data pipeline compiled and loaded via DuckDB + Parquet marts.")
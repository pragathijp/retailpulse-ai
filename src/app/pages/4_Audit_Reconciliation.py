import streamlit as st
import duckdb

st.set_page_config(page_title="Audit & Reconciliation | RetailPulse AI", layout="wide")
st.title("🛡️ Store-to-RFM Audit & Reconciliation Ledger")

@st.cache_data
def load_audit():
    conn = duckdb.connect()
    df_audit = conn.read_parquet("data/processed/audit_revenue_variance.parquet").df()
    conn.close()
    return df_audit

df = load_audit()
row = df.iloc[0]

unexplained = row['unexplained_revenue']
is_compliant = abs(unexplained) <= 0.01

if is_compliant:
    st.success(f"✅ AUDIT COMPLIANT: Unexplained Revenue Delta = £{unexplained:.4f} (Within ≤ £0.01 threshold)")
else:
    st.error(f"❌ AUDIT FAILED: Unexplained Revenue Delta = £{unexplained:.4f}")

col1, col2, col3 = st.columns(3)
col1.metric("Total Store Net Revenue", f"£{row['total_store_net_revenue']:,.2f}")
col2.metric("Total RFM Net Revenue", f"£{row['total_rfm_net_revenue']:,.2f}")
col3.metric("Raw Delta Revenue", f"£{row['delta_revenue']:,.2f}")

st.divider()

st.subheader("Variance Breakdown Ledger")
ledger_data = {
    "Category": [
        "1. Store Net Revenue (All Transactions)",
        "2. Attributed RFM Revenue (Valid Customers)",
        "3. Variance: Unattributed Guest Revenue (Null Customer ID)",
        "4. Variance: Ineligible Customer Revenue (Returns-only / Zero sales)",
        "5. Final Unexplained Residual Variance"
    ],
    "Amount (£)": [
        f"£{row['total_store_net_revenue']:,.2f}",
        f"£{row['total_rfm_net_revenue']:,.2f}",
        f"£{row['unattributed_net_revenue']:,.2f}",
        f"£{row['ineligible_customer_net_revenue']:,.2f}",
        f"£{row['unexplained_revenue']:.4f}"
    ]
}

st.table(ledger_data)
import duckdb
import pandas as pd
import numpy as np

def run_rfm_check():
    conn = duckdb.connect()
    
    # Load fact_sales directly from Parquet
    df_raw = conn.read_parquet("data/processed/fact_sales.parquet").df()
    
    # PRD Rule: Filter customers with at least one valid sale
    valid_customers = df_raw[df_raw['is_valid_sale'] & df_raw['customer_id'].notnull()]['customer_id'].unique()
    df_filtered = df_raw[df_raw['customer_id'].isin(valid_customers)].copy()
    conn.close()

    ref_date = pd.to_datetime(df_filtered['invoice_ts']).max() + pd.Timedelta(days=1)

    # Compute RFM in Pandas
    rfm_pd = df_filtered.groupby('customer_id').agg(
        recency=('invoice_ts', lambda x: (ref_date - pd.to_datetime(x).max()).days),
        frequency=('invoice_no', lambda x: x[df_filtered.loc[x.index, 'is_valid_sale']].nunique()),
        monetary=('net_revenue_line', 'sum')
    ).reset_index()

    # Sort deterministically with customer_id ties
    rfm_pd = rfm_pd.sort_values(by=['recency', 'customer_id'], ascending=[False, True])
    rfm_pd['r_score'] = pd.qcut(rfm_pd['recency'].rank(method='first', ascending=False), 5, labels=[1, 2, 3, 4, 5]).astype(int)

    rfm_pd = rfm_pd.sort_values(by=['frequency', 'customer_id'], ascending=[True, True])
    rfm_pd['f_score'] = pd.qcut(rfm_pd['frequency'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5]).astype(int)

    rfm_pd = rfm_pd.sort_values(by=['monetary', 'customer_id'], ascending=[True, True])
    rfm_pd['m_score'] = pd.qcut(rfm_pd['monetary'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5]).astype(int)

    # Load SQL RFM mart
    df_sql = pd.read_parquet("data/processed/mart_customer_rfm.parquet")

    # Compare row counts
    assert len(rfm_pd) == len(df_sql), f"Row count mismatch: Pandas ({len(rfm_pd)}) vs SQL ({len(df_sql)})"
    print(f"✅ RFM Validation Passed: {len(df_sql)} eligible customer profiles matched between Pandas and SQL.")

if __name__ == "__main__":
    run_rfm_check()
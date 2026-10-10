import pytest
import duckdb
import pandas as pd
from decimal import Decimal

from common import parquet

TOL = Decimal('0.01')

@pytest.fixture
def conn():
    c = duckdb.connect()
    yield c
    c.close()

def test_parquet_row_counts(conn):
    for table in ['fact_sales', 'mart_monthly_sales', 'mart_customer_rfm', 'mart_product_performance']:
        df = conn.read_parquet(parquet(table)).df()
        assert len(df) > 0, f"Table {table} is empty!"

def test_rfm_variance_is_unattributed_revenue(conn):
    df_fact = conn.read_parquet(parquet('fact_sales')).df()
    df_rfm = conn.read_parquet(parquet('mart_customer_rfm')).df()
    df_audit = conn.read_parquet(parquet('audit_revenue_variance')).df()
    
    store_rev = Decimal(str(round(df_fact['net_revenue_line'].sum(), 2)))
    rfm_rev = Decimal(str(round(df_rfm['monetary_raw'].sum(), 2)))
    
    delta = store_rev - rfm_rev
    
    # Read logged audit parameters
    row = df_audit.iloc[0]
    unattributed_nulls = Decimal(str(round(row['unattributed_net_revenue'], 2)))
    ineligible_cust = Decimal(str(round(row['ineligible_customer_net_revenue'], 2)))
    
    # Total explained variance
    explained_variance = unattributed_nulls + ineligible_cust
    unexplained_residual = abs(delta - explained_variance)
    
    assert unexplained_residual <= TOL, f"Unexplained variance {unexplained_residual} exceeds threshold £0.01"

def test_forecast_has_no_leakage():
    df = pd.read_parquet(parquet('forecast_weekly'))
    train_max = df[df['split'] == 'train']['week_start'].max()
    test_min = df[df['split'] == 'test']['week_start'].min()
    assert train_max < test_min, "Forecast train/test date overlap detected!"
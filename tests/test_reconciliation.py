"""Cross-layer reconciliation: independent SQL, dbt fact and marts, Parquet exports. Tolerance 0.01 GBP."""
import pandas as pd
import pytest

from common import parquet
from helpers import close, parquet_rows, parquet_sum, scalar

RETURN_COND = "(coalesce(invoice_no like 'C%', false) or quantity < 0)"
RAW_NET_SQL = f'''
select
  coalesce(sum(case when not {RETURN_COND} and quantity > 0 and unit_price > 0
                    then quantity * unit_price end), 0)
  - coalesce(sum(case when {RETURN_COND} and unit_price > 0
                      then abs(quantity) * unit_price end), 0)
from stg_retail_transactions
'''

EXPORTED = ['fact_sales', 'dim_date', 'mart_monthly_sales', 'mart_product_performance',
            'mart_customer_rfm', 'audit_revenue_variance']
SUMS = [
    ('fact_sales', 'net_revenue_line'),
    ('fact_sales', 'gross_sales'),
    ('fact_sales', 'return_amount'),
    ('mart_monthly_sales', 'net_revenue'),
    ('mart_monthly_sales', 'gross_sales'),
    ('mart_product_performance', 'net_revenue'),
    ('mart_customer_rfm', 'monetary_raw'),
]


# --- revenue definition ---------------------------------------------------------------------

def test_independent_recompute_matches_fact(con):
    assert close(scalar(con, RAW_NET_SQL), scalar(con, 'select sum(net_revenue_line) from fact_sales'))


def test_independent_recompute_matches_parquet(con):
    assert close(scalar(con, RAW_NET_SQL), parquet_sum('fact_sales', 'net_revenue_line'))


def test_net_equals_gross_minus_returns(con):
    gross = scalar(con, 'select sum(gross_sales) from fact_sales')
    ret = scalar(con, 'select sum(return_amount) from fact_sales')
    net = scalar(con, 'select sum(net_revenue_line) from fact_sales')
    assert close(gross - ret, net)


def test_no_line_is_both_sale_and_return(con):
    bad = con.execute('select count(*) from fact_sales where (is_valid_sale and is_return) '
                      'or (gross_sales > 0 and return_amount > 0)').fetchone()[0]
    assert bad == 0


def test_zero_price_lines_carry_no_revenue(con):
    bad = con.execute('select count(*) from fact_sales where unit_price <= 0 and net_revenue_line <> 0').fetchone()[0]
    assert bad == 0


# --- marts agree with the fact ----------------------------------------------------------------

def test_monthly_mart_matches_fact(con):
    assert close(scalar(con, 'select sum(net_revenue) from mart_monthly_sales'),
                 scalar(con, 'select sum(net_revenue_line) from fact_sales'))


def test_product_plus_non_product_equals_store_total(con):
    non_product = scalar(con, 'select sum(net_revenue_line) from fact_sales where is_non_product')
    assert close(parquet_sum('mart_product_performance', 'net_revenue') + non_product,
                 scalar(con, 'select sum(net_revenue_line) from fact_sales'))


def test_last_month_partial_flag_is_correct(con):
    flagged = con.execute('select bool_or(is_partial_month) from mart_monthly_sales '
                          'where sales_month = (select max(sales_month) from mart_monthly_sales)').fetchone()[0]
    expected = con.execute("select max(invoice_date) < cast(date_trunc('month', max(invoice_date)) "
                           "+ interval 1 month - interval 1 day as date) from fact_sales").fetchone()[0]
    assert flagged == expected


def test_dim_date_covers_every_invoice_date(con):
    missing = con.execute('select count(*) from fact_sales f left join dim_date d on f.invoice_date = d.date_key '
                          'where d.date_key is null').fetchone()[0]
    assert missing == 0


# --- RFM and the null-customer variance -------------------------------------------------------

def test_rfm_variance_is_fully_explained(con):
    store = scalar(con, 'select sum(net_revenue_line) from fact_sales')
    rfm = scalar(con, 'select sum(monetary_raw) from mart_customer_rfm')
    null_id = scalar(con, 'select sum(net_revenue_line) from fact_sales where customer_id is null')
    ineligible = scalar(con, 'select sum(net_revenue_line) from fact_sales where customer_id is not null '
                             'and customer_id not in (select customer_id from mart_customer_rfm)')
    assert close(store - rfm, null_id + ineligible)
    assert close(scalar(con, 'select delta_revenue from audit_revenue_variance'), store - rfm)
    assert close(scalar(con, 'select unexplained_revenue from audit_revenue_variance'), 0)


def test_rfm_excludes_null_customers_but_fact_keeps_them(con):
    assert con.execute('select count(*) from mart_customer_rfm where customer_id is null').fetchone()[0] == 0
    assert con.execute('select count(*) from fact_sales where customer_id is null').fetchone()[0] > 0


def test_rfm_population_is_customers_with_a_valid_sale(con):
    expected = con.execute('select count(distinct customer_id) from fact_sales '
                           'where is_valid_sale and customer_id is not null').fetchone()[0]
    assert con.execute('select count(*) from mart_customer_rfm').fetchone()[0] == expected


# --- row-count ledger -------------------------------------------------------------------------

def test_row_ledger_balances_against_raw_table(con):
    ledger = dict(con.execute('select check_name, check_value from audit_data_quality').fetchall())
    raw = con.execute('select count(*) from raw.retail_transactions').fetchone()[0]
    assert int(ledger['raw_rows']) == raw
    assert raw == int(ledger['staged_rows'] + ledger['exact_duplicates_removed'] + ledger['invalid_rows_dropped'])
    assert int(ledger['staged_rows']) == con.execute('select count(*) from fact_sales').fetchone()[0]


# --- Parquet exports equal the database -------------------------------------------------------

@pytest.mark.parametrize('table,col', SUMS, ids=[f'{t}.{c}' for t, c in SUMS])
def test_parquet_sum_matches_duckdb(con, table, col):
    assert close(scalar(con, f'select sum({col}) from {table}'), parquet_sum(table, col))


@pytest.mark.parametrize('table', EXPORTED)
def test_parquet_row_count_matches_duckdb(con, table):
    assert con.execute(f'select count(*) from {table}').fetchone()[0] == parquet_rows(table)


# --- forecast ---------------------------------------------------------------------------------

def test_forecast_has_no_leakage():
    path = parquet('forecast_weekly')
    try:
        df = pd.read_parquet(path)
    except OSError:
        pytest.skip('forecast_weekly.parquet not built yet: run python run.py forecast')
    assert df.loc[df['split'] == 'train', 'week_start'].max() < df.loc[df['split'] == 'test', 'week_start'].min()

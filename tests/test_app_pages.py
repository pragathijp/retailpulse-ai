"""Streamlit pages load without errors and show exactly the numbers in the contract, marts and audit ledger."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from common import ROOT
from helpers import CONTRACT, scalar

PAGES = sorted((ROOT / 'src' / 'app' / 'pages').glob('*.py'))
MONEY = {'gross_revenue', 'return_amount', 'net_revenue', 'aov'}


def run_page(name):
    path = next(p for p in PAGES if p.name == name)
    at = AppTest.from_file(str(path), default_timeout=120).run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def metrics(at):
    return {m.label: m.value for m in at.metric}


@pytest.mark.parametrize('page', [p.name for p in PAGES])
def test_every_page_loads_without_errors(page):
    run_page(page)


def test_main_app_loads():
    at = AppTest.from_file(str(ROOT / 'src' / 'app' / 'main.py'), default_timeout=60).run()
    assert not at.exception


def test_executive_kpis_equal_the_contract(con):
    shown = metrics(run_page('1_Executive_Overview.py'))
    for m in CONTRACT['metrics']:
        expected = scalar(con, f"select {m['sql']} from fact_sales")
        text = f'£{expected:,.2f}' if m['name'] in MONEY else f'{int(expected):,}'
        assert shown[m['dax_measure']] == text, m['name']


def test_customer_page_equals_rfm_mart_and_audit(con):
    shown = metrics(run_page('2_Customer_RFM.py'))
    assert shown['Total Tracked Customers'] == f"{con.execute('select count(*) from mart_customer_rfm').fetchone()[0]:,}"
    rfm_total = scalar(con, 'select sum(monetary_raw) from mart_customer_rfm')
    assert shown['Total Customer Net Revenue (RFM)'] == f'£{rfm_total:,.2f}'
    assert shown['Total Customer Net Revenue (RFM)'] == \
        f"£{scalar(con, 'select total_rfm_net_revenue from audit_revenue_variance'):,.2f}"


def test_product_page_equals_pareto_analysis(con):
    shown = metrics(run_page('3_Product_Performance.py'))
    total = con.execute('select count(*) from mart_product_performance').fetchone()[0]
    ranked = con.execute('select count(*) from mart_product_performance where pareto_rank is not null').fetchone()[0]
    top80 = con.execute('select count(*) from mart_product_performance where is_top_80').fetchone()[0]
    assert shown['Total Products'] == f'{total:,}'
    assert shown['Ranked Products (positive revenue)'] == f'{ranked:,}'
    assert shown['Top 80% Revenue Products'] == f'{top80:,}'
    assert shown['Pareto Density (% of ranked SKUs)'] == f'{top80 / ranked * 100:.2f}%'


def test_audit_page_equals_the_variance_ledger(con):
    at = run_page('4_Audit_Reconciliation.py')
    shown = metrics(at)
    assert shown['Total Store Net Revenue'] == f"£{scalar(con, 'select total_store_net_revenue from audit_revenue_variance'):,.2f}"
    assert shown['Total RFM Net Revenue'] == f"£{scalar(con, 'select total_rfm_net_revenue from audit_revenue_variance'):,.2f}"
    assert shown['Raw Delta Revenue'] == f"£{scalar(con, 'select delta_revenue from audit_revenue_variance'):,.2f}"
    assert len(at.success) == 1 and not at.error


def test_forecast_page_names_the_measured_best_model():
    import pandas as pd
    from common import parquet

    m = pd.read_parquet(parquet('forecast_metrics'))
    shown = metrics(run_page('6_Forecast.py'))
    assert shown['Best model (lowest holdout MAE)'] == m[m['is_best']].iloc[0]['model']

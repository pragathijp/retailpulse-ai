"""The context sent to the model comes from the marts and uses the contract definitions."""
import json

import pytest

from ai_assistant import ask, unsupported_numbers
from context_builder import build_context, parse_month, select_sections
from helpers import CONTRACT, close, scalar


@pytest.fixture(scope='module')
def ctx():
    return build_context('Which products declined the most last month?')


def test_store_totals_use_the_contract_sql(con, ctx):
    row = ctx['sections']['store_totals']['rows'][0]
    for m in CONTRACT['metrics']:
        assert close(row[m['name']], scalar(con, f"select {m['sql']} from fact_sales"), 0.01), m['name']


def test_aov_is_gross_over_orders_as_in_the_contract(ctx):
    row = ctx['sections']['store_totals']['rows'][0]
    assert abs(row['aov'] - row['gross_revenue'] / row['order_count']) < 0.01


def test_reference_month_is_a_complete_month(con, ctx):
    partial = con.execute("select bool_or(is_partial_month) from mart_monthly_sales where sales_month = date '"
                          + ctx['meta']['reference_month'] + "-01'").fetchone()[0]
    assert partial is False


def test_top_product_is_the_largest_in_the_mart(con, ctx):
    top = ctx['sections']['top_products']['rows'][0]
    assert close(top['net_revenue'], scalar(con, 'select max(net_revenue) from mart_product_performance'), 0.01)


def test_declines_are_negative_and_sorted(ctx):
    changes = [r['change'] for r in ctx['sections']['product_declines']['rows']]
    assert changes == sorted(changes) and changes[0] <= 0


def test_variance_section_matches_the_audit_table(con):
    c = build_context('what is the unexplained variance')
    row = c['sections']['revenue_variance']['rows'][0]
    assert close(row['delta_revenue'], scalar(con, 'select delta_revenue from audit_revenue_variance'), 0.01)
    assert abs(row['unexplained_revenue']) <= 0.01


def test_router_selects_sections_by_question():
    assert 'forecast_metrics' in build_context('what is the forecast')['sections']
    assert 'forecast_metrics' not in build_context('top products by revenue')['sections']
    assert 'rfm_segments' in build_context('how many champions')['sections']
    assert select_sections('hello') == list(select_sections('hello'))  # falls back to all sections
    assert len(select_sections('hello')) == 6


def test_month_parsing():
    assert str(parse_month('revenue in 2011-10')) == '2011-10-01'
    assert str(parse_month('what happened in October 2010?')) == '2010-10-01'
    assert parse_month('last month') is None


def test_context_is_small_and_json_serialisable(ctx):
    assert len(json.dumps(ctx, default=str)) < 25_000


def test_real_context_supports_a_grounded_answer_and_rejects_a_wrong_one(ctx):
    net = ctx['sections']['store_totals']['rows'][0]['net_revenue']
    good = ask('Total net revenue?', context=ctx, complete=lambda s, u: f'Net revenue was {net:,.2f} GBP.')
    assert good['verified']
    assert unsupported_numbers(f'Net revenue was {net + 1:,.2f} GBP.', ctx) != []

"""The metrics contract is executable: every KPI SQL runs, is consistent, and matches the Power BI export."""
import pandas as pd
import pytest

from common import ROOT
from helpers import CONTRACT, close, scalar

METRICS = CONTRACT['metrics']
EXPECTED_NAMES = ['gross_revenue', 'return_amount', 'net_revenue', 'order_count', 'units_sold', 'aov']


def test_contract_is_complete():
    assert [m['name'] for m in METRICS] == EXPECTED_NAMES
    for m in METRICS:
        for key in ('description', 'sql', 'dax', 'dax_measure', 'tolerance'):
            assert key in m and m[key] not in (None, ''), f'{m["name"]} missing {key}'
    assert CONTRACT['tolerance_abs'] == 0.01
    assert len({m['dax_measure'] for m in METRICS}) == len(METRICS)


@pytest.mark.parametrize('metric', METRICS, ids=[m['name'] for m in METRICS])
def test_contract_sql_executes_and_is_positive(con, metric):
    value = scalar(con, f"select {metric['sql']} from {CONTRACT['source_table']}")
    assert value > 0, metric['name']


def test_contract_metrics_are_mutually_consistent(con):
    v = {m['name']: scalar(con, f"select {m['sql']} from {CONTRACT['source_table']}") for m in METRICS}
    assert close(v['gross_revenue'] - v['return_amount'], v['net_revenue'])
    assert close(v['gross_revenue'] / v['order_count'], v['aov'])


def test_powerbi_kpis_match_contract(con):
    f = ROOT / CONTRACT['bi_export']['file']
    if not f.exists():
        pytest.skip('Power BI KPI export not found: export KPIs to data/bi_exports/pbi_kpis.csv (Phase 6)')
    bi = pd.read_csv(f)
    bi.columns = [c.strip().strip('[]').strip() for c in bi.columns]
    values = dict(zip(bi['metric'].astype(str).str.strip(), bi['value']))
    for m in METRICS:
        assert m['name'] in values, f"missing KPI {m['name']} in the Power BI export"
        expected = scalar(con, f"select {m['sql']} from {CONTRACT['source_table']}")
        assert close(values[m['name']], expected, m['tolerance']), f"{m['name']}: BI {values[m['name']]} vs SQL {expected}"

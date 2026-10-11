"""Store-level KPIs computed with the SQL expressions in metrics_contract.yml.

The contract is the single definition of every KPI. The Streamlit app, the AI context and the tests all
read their store totals through this module, never through their own formulas.
"""
import sys
from decimal import Decimal
from pathlib import Path

import duckdb
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CONTRACT_PATH, parquet  # noqa: E402

MONEY = {'gross_revenue', 'return_amount', 'net_revenue', 'aov'}


def store_kpis():
    """Return [{'name', 'label', 'value'}] for every contract metric, evaluated on fact_sales.parquet."""
    contract = yaml.safe_load(CONTRACT_PATH.read_text())
    con = duckdb.connect()
    con.execute(f"create view fact_sales as select * from read_parquet('{parquet('fact_sales')}')")
    out = []
    for m in contract['metrics']:
        value = con.execute(f"select {m['sql']} from fact_sales").fetchone()[0]
        out.append({'name': m['name'], 'label': m['dax_measure'], 'value': Decimal(str(value))})
    con.close()
    return out


def format_kpi(name, value):
    return f'£{value:,.2f}' if name in MONEY else f'{int(value):,}'

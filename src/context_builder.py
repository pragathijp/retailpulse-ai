#!/usr/bin/env python3
"""Build a compact, pre-aggregated JSON context for the grounded assistant.

Every number comes from the Parquet marts. Store-level KPIs are computed with the SQL expressions in
metrics_contract.yml, so the assistant can never see a different definition from dbt, Power BI or the tests.

Usage: python src/context_builder.py "Which products declined most last month?"
"""
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import duckdb
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import AI_CONTEXT_DIR, CONTRACT_PATH, PROC  # noqa: E402

TABLES = ['fact_sales', 'mart_monthly_sales', 'mart_product_performance', 'mart_customer_rfm',
          'audit_revenue_variance', 'forecast_metrics', 'forecast_weekly']
RATE_COLS = {'return_rate', 'delta_pct', 'retention_rate', 'cumulative_share'}
MONTHS = {'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6, 'july': 7,
          'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12}
KEYWORDS = {
    'monthly': ['revenue', 'sales', 'month', 'growth', 'trend', 'order', 'aov', 'return', 'decline', 'drop'],
    'products': ['product', 'sku', 'item', 'stock', 'top', 'best', 'worst', 'decline', 'drop', 'gain', 'category', 'pareto'],
    'countries': ['country', 'countries', 'region', 'geograph', 'market'],
    'rfm': ['customer', 'segment', 'rfm', 'champion', 'churn', 'risk', 'loyal', 'hibernat'],
    'variance': ['variance', 'missing', 'unattributed', 'unexplained', 'reconcil', 'null', 'guest'],
    'forecast': ['forecast', 'predict', 'next', 'expect', 'projection', 'baseline'],
}


def clean(value, col=None):
    if isinstance(value, Decimal):
        value = float(value)
    if isinstance(value, float):
        if value != value:
            return None
        return round(value, 4 if col in RATE_COLS else 2)
    if isinstance(value, (date, datetime)):
        return value.isoformat()[:10]
    return value


def rows(con, sql):
    cur = con.execute(sql)
    names = [d[0] for d in cur.description]
    return [{n: clean(v, n) for n, v in zip(names, r)} for r in cur.fetchall()]


def parse_month(question):
    """First day of a month named in the question ('2011-10' or 'October 2011'), else None."""
    m = re.search(r'(20[0-9]{2})-([01][0-9])', question)
    if m:
        return date(int(m.group(1)), int(m.group(2)), 1)
    low = question.lower()
    for name, num in MONTHS.items():
        m = re.search(name + r'[ ,]+(20[0-9]{2})', low)
        if m:
            return date(int(m.group(1)), num, 1)
    return None


def select_sections(question):
    low = question.lower()
    chosen = [k for k, words in KEYWORDS.items() if any(w in low for w in words)]
    return chosen or list(KEYWORDS)


def section(source_table, period, data):
    return {'source_table': source_table, 'period': period, 'row_count': len(data), 'rows': data}


def build_context(question='overview', proc=PROC):
    con = duckdb.connect()
    for t in TABLES:
        path = Path(proc) / f'{t}.parquet'
        if path.exists():
            con.execute(f"create view {t} as select * from read_parquet('{path.as_posix()}')")
    contract = yaml.safe_load(CONTRACT_PATH.read_text())

    last_full = rows(con, '''select max(sales_month) as m from (
        select sales_month, bool_or(is_partial_month) as p from mart_monthly_sales group by sales_month
        ) where not p''')[0]['m']
    focus = parse_month(question) or date.fromisoformat(last_full)
    prev = (focus - timedelta(days=1)).replace(day=1)
    wanted = select_sections(question)
    sections = {}

    kpis = ', '.join(f"{m['sql']} as {m['name']}" for m in contract['metrics'])
    sections['store_totals'] = section('fact_sales', 'full dataset', rows(con, f'''
        select {kpis}, min(invoice_date) as first_date, max(invoice_date) as last_date,
               count(distinct customer_id) as identified_customers
        from fact_sales'''))

    if 'monthly' in wanted:
        sections['monthly_totals'] = section('mart_monthly_sales', 'last 13 months', rows(con, '''
            select sales_month, net_revenue, gross_sales, return_amount, order_count, units_sold, aov, is_partial,
                   case when is_partial then null else round(100.0 * (net_revenue - prev) / nullif(prev, 0), 2) end as mom_pct
            from (select sales_month, sum(net_revenue) as net_revenue, sum(gross_sales) as gross_sales,
                         sum(return_amount) as return_amount, sum(order_count) as order_count,
                         sum(units_sold) as units_sold, sum(gross_sales) / nullif(sum(order_count), 0) as aov,
                         bool_or(is_partial_month) as is_partial,
                         lag(sum(net_revenue)) over (order by sales_month) as prev
                  from mart_monthly_sales group by sales_month)
            order by sales_month desc limit 13'''))
    if 'products' in wanted:
        sections['top_products'] = section('mart_product_performance', 'full dataset', rows(con, '''
            select stock_code, description, net_revenue, units_sold, return_rate
            from mart_product_performance order by net_revenue desc limit 10'''))
        movers = f'''
            with cur as (select stock_code, any_value(description) as description, sum(net_revenue_line) as net
                         from fact_sales where not is_non_product and sales_month = date '{focus.isoformat()}' group by stock_code),
                 prv as (select stock_code, any_value(description) as description, sum(net_revenue_line) as net
                         from fact_sales where not is_non_product and sales_month = date '{prev.isoformat()}' group by stock_code)
            select coalesce(c.stock_code, p.stock_code) as stock_code,
                   coalesce(c.description, p.description) as description,
                   coalesce(c.net, 0) as current_net_revenue, coalesce(p.net, 0) as previous_net_revenue,
                   coalesce(c.net, 0) - coalesce(p.net, 0) as change
            from cur c full join prv p on c.stock_code = p.stock_code'''
        period = f'{focus.isoformat()[:7]} vs {prev.isoformat()[:7]}'
        sections['product_declines'] = section('fact_sales', period, rows(con, movers + ' order by change asc limit 5'))
        sections['product_gains'] = section('fact_sales', period, rows(con, movers + ' order by change desc limit 5'))
    if 'countries' in wanted:
        sections['top_countries'] = section('mart_monthly_sales', 'full dataset', rows(con, '''
            select country, sum(net_revenue) as net_revenue from mart_monthly_sales
            group by country order by net_revenue desc limit 5'''))
    if 'rfm' in wanted:
        sections['rfm_segments'] = section('mart_customer_rfm', 'full dataset', rows(con, '''
            select segment, count(*) as customers, sum(monetary_raw) as net_revenue
            from mart_customer_rfm group by segment order by net_revenue desc'''))
    if 'variance' in wanted:
        sections['revenue_variance'] = section('audit_revenue_variance', 'full dataset',
                                               rows(con, 'select * exclude (run_ts) from audit_revenue_variance'))
    if 'forecast' in wanted:
        sections['forecast_metrics'] = section('forecast_metrics', 'holdout', rows(con, 'select * from forecast_metrics'))
        sections['forecast_next_weeks'] = section('forecast_weekly', 'next 8 weeks', rows(con, '''
            select week_start, forecast, lower, upper from forecast_weekly where is_future order by week_start'''))

    meta = {
        'currency': 'GBP',
        'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'reference_month': focus.isoformat()[:7],
        'previous_month': prev.isoformat()[:7],
        'definitions': {m['name']: m['description'] for m in contract['metrics']},
        'notes': ['Last month means the most recent complete month; the final month of data is partial and excluded.',
                  'There is no product category field; product means stock code.',
                  'Revenue includes lines with no customer id; RFM excludes them.'],
    }
    return {'meta': meta, 'sections': sections}


def main(argv):
    question = ' '.join(argv) or 'overview'
    ctx = build_context(question)
    AI_CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
    out = AI_CONTEXT_DIR / 'context.json'
    text = json.dumps(ctx, indent=2, default=str)
    out.write_text(text)
    print(f'Wrote {out} ({len(text) / 1024:.1f} KB) for question: {question!r}')
    print('Sections:', ', '.join(f"{k}({v['row_count']})" for k, v in ctx['sections'].items()))


if __name__ == '__main__':
    main(sys.argv[1:])

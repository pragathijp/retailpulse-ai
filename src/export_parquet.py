#!/usr/bin/env python3
"""Verify the Parquet deliverables that Power BI and the app read, and write a manifest.

Checks per file: exists, readable, row count equals the DuckDB view, required columns present.
Writes data/processed/_manifest.json (rows, bytes, sha256, columns). Exit code 1 on any failure.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DB_PATH, PROC  # noqa: E402

REQUIRED = {
    'fact_sales': ['transaction_line_key', 'invoice_no', 'stock_code', 'invoice_date', 'customer_id', 'country',
                   'is_return', 'is_non_product', 'is_valid_sale', 'gross_sales', 'return_amount', 'net_revenue_line'],
    'dim_date': ['date_key', 'year', 'month_num', 'year_month', 'month_start', 'week_start'],
    'mart_monthly_sales': ['sales_month', 'country', 'gross_sales', 'return_amount', 'net_revenue', 'order_count',
                           'units_sold', 'is_partial_month', 'mom_growth_pct'],
    'mart_product_performance': ['stock_code', 'description', 'net_revenue', 'units_sold', 'return_rate',
                                 'pareto_rank', 'cumulative_share', 'is_top_80'],
    'mart_customer_rfm': ['customer_id', 'recency_days', 'frequency', 'monetary_raw', 'r_score', 'f_score',
                          'm_score', 'rfm_score', 'segment'],
    'audit_revenue_variance': ['total_store_net_revenue', 'total_rfm_net_revenue', 'delta_revenue',
                               'unattributed_net_revenue', 'ineligible_customer_net_revenue', 'unexplained_revenue'],
}
OPTIONAL = ['forecast_weekly', 'forecast_metrics']


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    failures, manifest = [], {}
    con = duckdb.connect(str(DB_PATH), read_only=True)
    for name in list(REQUIRED) + OPTIONAL:
        path = PROC / f'{name}.parquet'
        if not path.exists():
            if name in REQUIRED:
                failures.append(f'{name}: file missing ({path})')
            continue
        meta = pq.read_metadata(path)
        columns = pq.read_schema(path).names
        entry = {'rows': meta.num_rows, 'bytes': path.stat().st_size, 'columns': columns, 'sha256': sha256(path)}
        if name in REQUIRED:
            missing = [c for c in REQUIRED[name] if c not in columns]
            if missing:
                failures.append(f'{name}: missing columns {missing}')
            n_db = con.execute(f'select count(*) from main.{name}').fetchone()[0]
            if n_db != meta.num_rows:
                failures.append(f'{name}: duckdb {n_db} rows vs parquet {meta.num_rows}')
        manifest[name] = entry
    con.close()
    out = {'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'files': manifest}
    (PROC / '_manifest.json').write_text(json.dumps(out, indent=2))
    if failures:
        print('EXPORT CHECK FAILED')
        for f in failures:
            print(' -', f)
        return 1
    print('Export verified:', {k: v['rows'] for k, v in manifest.items()})
    return 0


if __name__ == '__main__':
    sys.exit(main())

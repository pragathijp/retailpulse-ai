#!/usr/bin/env python3
"""Independent pandas recomputation of mart_customer_rfm. Exit code 1 on any mismatch.

NTILE(5) is reproduced exactly (not pandas qcut, which handles ties differently):
sort by the metric then customer_id, split into 5 buckets, the first (n mod 5) buckets get one extra row.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import SEEDS_DIR, parquet  # noqa: E402

REF_OFFSET_DAYS = 1  # must equal dbt var rfm_reference_date_offset_days
SEED = SEEDS_DIR / 'rfm_segment_map.csv'
COMPARE_COLUMNS = ['r_score', 'f_score', 'm_score', 'rfm_score', 'segment', 'frequency', 'recency_days']


def ntile(df, sort_cols, ascending, n=5):
    """Replicates SQL NTILE(n) OVER (ORDER BY sort_cols). Returns a Series aligned to df's index."""
    ordered = df.sort_values(sort_cols, ascending=ascending, kind='mergesort')
    q, r = divmod(len(ordered), n)
    sizes = [q + 1] * r + [q] * (n - r)
    scores = np.repeat(np.arange(1, n + 1), sizes)
    return pd.Series(scores, index=ordered.index)


def compute_rfm():
    cols = ['invoice_no', 'invoice_date', 'customer_id', 'is_valid_sale', 'net_revenue_line']
    f = pd.read_parquet(parquet('fact_sales'), columns=cols)
    f['invoice_date'] = pd.to_datetime(f['invoice_date'])
    f['net_revenue_line'] = f['net_revenue_line'].astype('float64')
    ref_date = f['invoice_date'].max() + pd.Timedelta(days=REF_OFFSET_DAYS)

    known = f[f['customer_id'].notna()]
    valid = known[known['is_valid_sale']]
    agg = valid.groupby('customer_id').agg(last_purchase_date=('invoice_date', 'max'),
                                           frequency=('invoice_no', 'nunique'))
    monetary_raw = known.groupby('customer_id')['net_revenue_line'].sum().round(4).rename('monetary_raw')
    m = agg.join(monetary_raw).reset_index()
    m['recency_days'] = (ref_date - m['last_purchase_date']).dt.days
    m['monetary'] = m['monetary_raw'].clip(lower=0)

    m['r_score'] = ntile(m, ['recency_days', 'customer_id'], [False, True])  # recent buyers score 5
    m['f_score'] = ntile(m, ['frequency', 'customer_id'], [True, True])
    m['m_score'] = ntile(m, ['monetary', 'customer_id'], [True, True])
    m['rfm_score'] = m['r_score'].astype(str) + m['f_score'].astype(str) + m['m_score'].astype(str)

    seg = pd.read_csv(SEED).sort_values('priority')
    m['segment'] = None
    for s in seg.itertuples():
        mask = (m['segment'].isna()
                & m['r_score'].between(s.r_min, s.r_max)
                & m['f_score'].between(s.f_min, s.f_max)
                & m['m_score'].between(s.m_min, s.m_max))
        m.loc[mask, 'segment'] = s.segment
    return m


def find_problems(py=None, sql=None):
    """Compare the pandas recomputation with the SQL mart; returns a list of problem descriptions."""
    py = compute_rfm() if py is None else py
    if sql is None:
        sql = pd.read_parquet(parquet('mart_customer_rfm'))
    sql = sql.copy()
    sql['monetary_raw'] = sql['monetary_raw'].astype('float64')
    problems = []
    if len(py) != len(sql):
        problems.append(f'customer count differs: pandas {len(py)} vs sql {len(sql)}')
    j = py.merge(sql, on='customer_id', how='outer', suffixes=('_py', '_sql'), indicator=True)
    only = j[j['_merge'] != 'both']
    if len(only):
        problems.append(f'{len(only)} customers present on only one side')
    both = j[j['_merge'] == 'both']
    for col in COMPARE_COLUMNS:
        bad = int((both[f'{col}_py'] != both[f'{col}_sql']).sum())
        if bad:
            problems.append(f'{col}: {bad} mismatches')
    bad_money = int(((both['monetary_raw_py'] - both['monetary_raw_sql']).abs() > 0.01).sum())
    if bad_money:
        problems.append(f'monetary_raw: {bad_money} mismatches above 0.01')
    return problems


def main():
    py = compute_rfm()
    problems = find_problems(py=py)
    print(f'Customers recomputed in pandas: {len(py)}')
    print(py['segment'].value_counts().to_string())
    if problems:
        print('RFM CROSS-CHECK FAILED')
        for p in problems:
            print(' -', p)
        return 1
    print(f'RFM CROSS-CHECK PASSED: all {len(py)} customers identical in pandas and SQL '
          f'(r, f, m, score, segment, frequency, recency, monetary)')
    return 0


if __name__ == '__main__':
    sys.exit(main())

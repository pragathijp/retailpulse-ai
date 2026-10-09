#!/usr/bin/env python3
# Load UCI Online Retail (I or II) into DuckDB raw.retail_transactions and write a profile report.
import argparse
import sys
from pathlib import Path
import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / 'data' / 'raw'
DB_PATH = ROOT / 'data' / 'duckdb' / 'retail_analytics.duckdb'
PROFILE_PATH = ROOT / 'reports' / 'data_profile.md'
NL = chr(10)
TABLE = 'raw.retail_transactions'

# Normalised source header (lower-case, no spaces or underscores) -> canonical column
HEADER_MAP = {
    'invoiceno': 'invoice_no',
    'invoice': 'invoice_no',       # Online Retail II
    'stockcode': 'stock_code',
    'description': 'description',
    'quantity': 'quantity',
    'invoicedate': 'invoice_ts',
    'unitprice': 'unit_price',
    'price': 'unit_price',          # Online Retail II
    'customerid': 'customer_id',    # CustomerID and Customer ID
    'country': 'country',
}

CANONICAL = [
    'invoice_no', 'stock_code', 'description', 'quantity',
    'invoice_ts', 'unit_price', 'customer_id', 'country'
]

NULL_TOKENS = ['', 'nan', 'NaN', 'NAN', 'None', 'NULL', 'null', '<NA>']


def norm_header(name):
    return str(name).strip().lower().replace(' ', '').replace('_', '')


def find_source(explicit):
    if explicit:
        path = Path(explicit)
        if not path.exists():
            sys.exit(f'File not found: {path}')
        return path
    found = sorted(
        list(RAW_DIR.glob('*.csv')) +
        list(RAW_DIR.glob('*.xlsx')) +
        list(RAW_DIR.glob('*.xls'))
    )
    if not found:
        sys.exit('No CSV/XLSX in data/raw. Download or place the UCI Online Retail file first.')
    return found[0]


def read_source(path):
    kwargs = dict(dtype=str, keep_default_na=False, na_values=NULL_TOKENS)
    if path.suffix.lower() == '.csv':
        try:
            return pd.read_csv(path, encoding='utf-8', **kwargs)
        except UnicodeDecodeError:
            return pd.read_csv(path, encoding='ISO-8859-1', **kwargs)
    sheets = pd.read_excel(path, sheet_name=None, dtype=str)
    return pd.concat(list(sheets.values()), ignore_index=True)


def detect_variant(columns):
    return 'online_retail_ii' if 'invoice' in {norm_header(c) for c in columns} else 'online_retail_i'


def normalise(df):
    mapped = {c: HEADER_MAP[norm_header(c)] for c in df.columns if norm_header(c) in HEADER_MAP}
    missing = sorted(set(CANONICAL) - set(mapped.values()))
    if missing:
        sys.exit(f'Schema drift: missing {missing}; found columns {list(df.columns)}')
    df = df.rename(columns=mapped)[CANONICAL].copy()
    for col in CANONICAL:
        df[col] = df[col].astype('string').str.strip()
        df[col] = df[col].mask(df[col].isin(NULL_TOKENS))
    
    # Float artifact cleanup: 17850.0 -> 17850
    df['customer_id'] = df['customer_id'].str.replace(r'\.0+$', '', regex=True)
    df['invoice_ts'] = pd.to_datetime(df['invoice_ts'], errors='coerce', format='mixed')
    return df


def load(df, variant):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    con.execute('create schema if not exists raw')
    con.register('src_df', df)
    con.execute(f'''
        create or replace table {TABLE} as
        select 
            invoice_no, 
            stock_code, 
            description,
            cast(try_cast(quantity as double) as integer) as quantity,
            cast(invoice_ts as timestamp) as invoice_ts,
            try_cast(unit_price as decimal(18,4)) as unit_price,
            customer_id, 
            country,
            '{variant}' as source_variant
        from src_df
    ''')
    con.unregister('src_df')
    return con


def profile(con, variant, source):
    def q(sql):
        return con.execute(sql).fetchone()[0]

    total = q(f'select count(*) from {TABLE}')
    nulls = {c: q(f'select count(*) from {TABLE} where {c} is null') for c in CANONICAL}
    dup_extra = q(
        f'select count(*) - (select count(*) from (select distinct * exclude (source_variant) from {TABLE})) from {TABLE}'
    )

    rows = [
        ('Total rows', total),
        ('Distinct invoices', q(f'select count(distinct invoice_no) from {TABLE}')),
        ('Return rows (invoice C* or quantity < 0)', q(f"select count(*) from {TABLE} where invoice_no like 'C%' or quantity < 0")),
        ('Negative quantity on non-C invoices', q(f"select count(*) from {TABLE} where quantity < 0 and invoice_no not like 'C%'")),
        ('Zero unit price rows', q(f'select count(*) from {TABLE} where unit_price = 0')),
        ('Negative unit price rows', q(f'select count(*) from {TABLE} where unit_price < 0')),
        ('Exact duplicate rows (extra copies)', dup_extra),
        ('Null customer_id %', round(100.0 * nulls['customer_id'] / total, 2)),
        ('First invoice_ts', q(f'select min(invoice_ts) from {TABLE}')),
        ('Last invoice_ts', q(f'select max(invoice_ts) from {TABLE}')),
    ]

    lines = [
        '# Raw Data Profile', '',
        f'- Source file: `{source.name}`',
        f'- Variant: `{variant}`', '',
        '## Summary', '',
        '| Metric | Value |',
        '|---|---|'
    ]
    lines += [f'| {k} | {v} |' for k, v in rows]
    lines += ['', '## Null counts', '', '| Column | Nulls |', '|---|---|']
    lines += [f'| {c} | {n} |' for c, n in nulls.items()]

    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_PATH.write_text(NL.join(lines) + NL)
    return nulls


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('file', nargs='?', help='path to raw CSV/XLSX (default: first file in data/raw)')
    args = ap.parse_args()

    source = find_source(args.file)
    raw = read_source(source)
    variant = detect_variant(raw.columns)
    df = normalise(raw)
    con = load(df, variant)
    nulls = profile(con, variant, source)
    con.close()

    bad = {c: nulls[c] for c in ('invoice_ts', 'quantity', 'unit_price') if nulls[c] > 0}
    if bad:
        sys.exit(f'Unparseable required fields (see reports/data_profile.md): {bad}')

    print(f'Loaded {len(df)} rows from {source.name} ({variant}) into {TABLE}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
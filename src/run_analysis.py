#!/usr/bin/env python3
"""Run compiled dbt analyses against DuckDB and save each result as reports/analysis_<name>.csv.

Usage:
    python src/run_analysis.py mom_growth
    python src/run_analysis.py --all
Requires `dbt compile` to have been run (python run.py analyses does both).
"""
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DB_PATH, DBT_DIR, REPORTS  # noqa: E402

COMPILED = DBT_DIR / 'target' / 'compiled' / 'retailpulse' / 'analyses'


def run_one(con, name, show=False):
    sql_path = COMPILED / f'{name}.sql'
    if not sql_path.exists():
        sys.exit(f'Compiled analysis not found: {sql_path}. Run: python run.py analyses')
    df = con.execute(sql_path.read_text()).df()
    REPORTS.mkdir(exist_ok=True)
    out = REPORTS / f'analysis_{name}.csv'
    df.to_csv(out, index=False)
    print(f'{name}: {len(df)} rows -> {out.name}')
    if show:
        print(df.head(15).to_string(index=False))
    return df


def main(argv):
    if not argv:
        sys.exit(__doc__)
    names = sorted(p.stem for p in COMPILED.glob('*.sql')) if argv[0] == '--all' else [argv[0]]
    con = duckdb.connect(str(DB_PATH), read_only=True)
    for name in names:
        run_one(con, name, show=argv[0] != '--all')
    con.close()


if __name__ == '__main__':
    main(sys.argv[1:])

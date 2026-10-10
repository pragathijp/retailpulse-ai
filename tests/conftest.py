import sys
from pathlib import Path

import duckdb
import pytest

# Make src/common.py importable from every test, regardless of the working directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from common import DB_PATH  # noqa: E402


@pytest.fixture(scope='session')
def con():
    """Read-only connection to the analytical database; fails clearly if the pipeline has not run."""
    if not DB_PATH.exists():
        pytest.fail(f'{DB_PATH} not found. Run: python run.py dbt_build')
    c = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        c.execute('select 1 from fact_sales limit 1').fetchone()
    except duckdb.Error as exc:
        pytest.fail(f'fact_sales is unreadable ({exc}). Rebuild with: python run.py dbt_build')
    yield c
    c.close()

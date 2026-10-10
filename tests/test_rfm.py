"""RFM: the pandas NTILE reproduction equals DuckDB NTILE (including ties) and the SQL mart equals pandas."""
import duckdb
import numpy as np
import pandas as pd
import pytest

from rfm_check import find_problems, ntile


def _frame(n, ties=40, seed=3):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({'customer_id': [str(10000 + i) for i in range(n)], 'v': rng.integers(0, ties, n)})


@pytest.mark.parametrize('n', [3, 5, 7, 100, 1003, 5878])
@pytest.mark.parametrize('desc', [False, True], ids=['asc', 'desc'])
def test_ntile_matches_duckdb_including_ties(n, desc):
    df = _frame(n)
    con = duckdb.connect()
    con.register('t', df)
    order = 'v desc, customer_id' if desc else 'v, customer_id'
    sql = con.execute(f'select customer_id, ntile(5) over (order by {order}) as s from t').df()
    expected = sql.set_index('customer_id')['s'].astype(int)
    mine = ntile(df, ['v', 'customer_id'], [not desc, True])
    mine.index = df.loc[mine.index, 'customer_id']  # translate row labels to customer ids
    assert (expected.sort_index() == mine.sort_index().astype(int)).all()


def test_ntile_bucket_sizes_differ_by_at_most_one():
    sizes = ntile(_frame(1003), ['v', 'customer_id'], [True, True]).value_counts()
    assert sizes.max() - sizes.min() <= 1 and set(sizes.index) == {1, 2, 3, 4, 5}


def test_sql_rfm_mart_equals_pandas_recomputation():
    assert find_problems() == []

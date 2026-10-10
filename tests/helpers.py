"""Shared helpers for the reconciliation suite (exact Decimal arithmetic, Parquet readers, contract loader)."""
from decimal import Decimal

import pyarrow.compute as pc
import pyarrow.parquet as pq
import yaml

from common import CONTRACT_PATH, PROC

CONTRACT = yaml.safe_load(CONTRACT_PATH.read_text())
TOL = Decimal(str(CONTRACT['tolerance_abs']))


def to_decimal(value):
    if value is None:
        return Decimal(0)
    return Decimal(str(value).replace(',', '').strip())


def scalar(con, sql):
    return to_decimal(con.execute(sql).fetchone()[0])


def parquet_sum(table, col):
    column = pq.read_table(PROC / f'{table}.parquet', columns=[col]).column(col)
    return to_decimal(pc.sum(column).as_py())


def parquet_rows(table):
    return pq.read_metadata(PROC / f'{table}.parquet').num_rows


def close(a, b, tol=TOL):
    return abs(to_decimal(a) - to_decimal(b)) <= Decimal(str(tol))

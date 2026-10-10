"""Shared paths for RetailPulse AI.

Every script, test and Streamlit page imports its locations from here, so nothing
depends on the current working directory. Paths are absolute and resolved from
this file's location.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / 'data'
RAW_DIR = DATA_DIR / 'raw'
DB_PATH = DATA_DIR / 'duckdb' / 'retail_analytics.duckdb'
PROC = DATA_DIR / 'processed'
BI_EXPORTS = DATA_DIR / 'bi_exports'
AI_CONTEXT_DIR = DATA_DIR / 'ai_context'
REPORTS = ROOT / 'reports'
DOCS = ROOT / 'docs'
DBT_DIR = ROOT / 'dbt_project'
SEEDS_DIR = DBT_DIR / 'seeds'
CONTRACT_PATH = ROOT / 'metrics_contract.yml'


def parquet(name):
    """Absolute, forward-slash path string of a processed Parquet file (safe for DuckDB and pandas)."""
    return (PROC / f'{name}.parquet').as_posix()

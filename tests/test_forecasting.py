"""Forecast outputs: no leakage, complete weeks, reconciles to the fact table, metrics are well formed."""
import numpy as np
import pandas as pd
import pytest

from common import parquet
from forecasting import interval, score, seasonal_naive
from helpers import close, scalar


@pytest.fixture(scope='module')
def weekly():
    try:
        return pd.read_parquet(parquet('forecast_weekly'))
    except OSError:
        pytest.skip('forecast_weekly.parquet not built: run python run.py forecast')


@pytest.fixture(scope='module')
def metrics():
    try:
        return pd.read_parquet(parquet('forecast_metrics'))
    except OSError:
        pytest.skip('forecast_metrics.parquet not built: run python run.py forecast')


def test_no_leakage_between_train_and_test(weekly):
    assert weekly.loc[weekly['split'] == 'train', 'week_start'].max() < weekly.loc[weekly['split'] == 'test', 'week_start'].min()


def test_split_is_80_20(weekly):
    n_train, n_test = (weekly['split'] == 'train').sum(), (weekly['split'] == 'test').sum()
    assert n_train == int((n_train + n_test) * 0.8)


def test_future_rows(weekly):
    future = weekly[weekly['split'] == 'future']
    assert len(future) == 8 and future['actual'].isna().all() and future['is_future'].all()
    assert future['forecast'].notna().all() and (future['lower'] <= future['upper']).all()


def test_weeks_are_contiguous_mondays(weekly):
    dates = pd.to_datetime(weekly['week_start'])
    assert (dates.dt.weekday == 0).all()
    assert (dates.diff().dropna() == pd.Timedelta(days=7)).all()


def test_weeks_are_complete_and_reconcile_to_fact(con, weekly):
    hist = weekly[weekly['split'] != 'future']
    first, last = pd.to_datetime(hist['week_start']).min(), pd.to_datetime(hist['week_start']).max()
    lo, hi = con.execute('select min(invoice_date), max(invoice_date) from fact_sales').fetchone()
    assert first >= pd.Timestamp(lo) and last + pd.Timedelta(days=6) <= pd.Timestamp(hi)
    expected = scalar(con, f"select sum(net_revenue_line) from fact_sales where invoice_date between date '{first.date()}' "
                           f"and date '{(last + pd.Timedelta(days=6)).date()}'")
    assert close(hist['actual'].sum(), expected, 0.05)


def test_metrics_shape(metrics):
    assert {'naive', 'moving_avg_4w', 'holt_winters'} <= set(metrics['model'])
    for col in ['mae', 'mape', 'wape', 'improvement_mae_pct_vs_naive', 'beats_naive', 'is_best', 'n_train', 'n_test']:
        assert col in metrics.columns
    assert metrics['mae'].notna().all() and (metrics['mae'] >= 0).all()
    assert metrics.loc[metrics['model'] == 'naive', 'improvement_mae_pct_vs_naive'].iloc[0] == 0
    assert metrics['is_best'].sum() >= 1


def test_score_known_values():
    s = score([100, 200, 0], [110, 180, 5])
    assert s['mae'] == pytest.approx(35 / 3)
    assert s['mape'] == pytest.approx((10 / 100 + 20 / 200) / 2 * 100)  # zero actual excluded
    assert s['wape'] == pytest.approx(35 / 300 * 100)


def test_seasonal_naive_uses_only_history():
    hist = np.arange(100, dtype=float)
    assert list(seasonal_naive(hist, 80, 3)) == [28.0, 29.0, 30.0]
    assert np.isnan(seasonal_naive(hist, 40, 2)).all()  # not enough history


def test_interval_is_clipped_and_widens():
    lo, hi = interval(np.array([10.0, 10.0, 10.0]), 5.0)
    assert (lo >= 0).all() and hi[2] - lo[2] >= hi[0] - lo[0]

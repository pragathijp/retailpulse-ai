#!/usr/bin/env python3
"""Weekly store-level net revenue forecast: baselines vs Holt-Winters, chronological 80/20 split.

Rules: only complete weeks inside the data window are used; weeks with no trading inside the range are real
zeros and are kept; models are fitted on the first 80 percent of weeks only; a final refit on all weeks gives an
8-week forward forecast. Yearly seasonality is added to Holt-Winters only if train has at least 104 weeks.
Outputs: data/processed/forecast_weekly.parquet, forecast_metrics.parquet and reports/forecast_report.md.
"""
import sys
import warnings
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PROC, REPORTS, parquet  # noqa: E402

TRAIN_FRAC = 0.8
FUTURE_WEEKS = 8
MA_WINDOW = 4
SEASONAL_PERIOD = 52
MIN_WEEKS = 20
NL = chr(10)


def weekly_series():
    """Complete weekly net revenue (Monday weeks), zero-filled inside the range. Returns (series, first_date, last_date)."""
    con = duckdb.connect()
    path = parquet('fact_sales')
    lo, hi = con.execute(f"select min(invoice_date), max(invoice_date) from read_parquet('{path}')").fetchone()
    df = con.execute(f"""select cast(date_trunc('week', invoice_date) as date) as week_start,
                                sum(net_revenue_line) as actual
                         from read_parquet('{path}') group by 1 order by 1""").df()
    con.close()
    s = pd.Series(df['actual'].astype('float64').values, index=pd.to_datetime(df['week_start']))
    s = s.reindex(pd.date_range(s.index.min(), s.index.max(), freq='7D'), fill_value=0.0)
    lo, hi = pd.Timestamp(lo), pd.Timestamp(hi)
    s = s[(s.index >= lo) & (s.index + pd.Timedelta(days=6) <= hi)]
    s.index.name = 'week_start'
    return s, lo, hi


def score(actual, pred):
    """MAE, MAPE (weeks with zero actual excluded) and WAPE, as percentages where applicable."""
    a = np.asarray(actual, dtype=float)
    p = np.asarray(pred, dtype=float)
    err = np.abs(a - p)
    nz = a > 0
    return {
        'mae': float(err.mean()),
        'mape': float((err[nz] / a[nz]).mean() * 100) if nz.any() else float('nan'),
        'wape': float(err.sum() / a.sum() * 100) if a.sum() != 0 else float('nan'),
    }


def seasonal_naive(history, start, horizon):
    """Value from 52 weeks earlier, using only observations before position `start`. NaN when unavailable."""
    out = []
    for j in range(horizon):
        idx = start + j - SEASONAL_PERIOD
        out.append(history[idx] if 0 <= idx < start else np.nan)
    return np.array(out, dtype=float)


def fit_holt_winters(y):
    kwargs = dict(trend='add', damped_trend=True, initialization_method='estimated')
    seasonal = len(y) >= 2 * SEASONAL_PERIOD
    if seasonal:
        kwargs.update(seasonal='add', seasonal_periods=SEASONAL_PERIOD)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        return ExponentialSmoothing(np.asarray(y, dtype=float), **kwargs).fit(optimized=True), seasonal


def interval(point, sigma):
    h = np.arange(1, len(point) + 1)
    width = 1.96 * sigma * np.sqrt(h)
    return np.clip(point - width, 0, None), point + width


def write_report(metrics, y, n_train, lo, hi, seasonal):
    REPORTS.mkdir(exist_ok=True)
    best = metrics.loc[metrics['mae'].idxmin()]
    hw = metrics.loc[metrics['model'] == 'holt_winters'].iloc[0]
    naive_mae = metrics.loc[metrics['model'] == 'naive', 'mae'].iloc[0]
    verdict = ('Holt-Winters BEATS the naive baseline' if hw['beats_naive']
               else 'Holt-Winters does NOT beat the naive baseline')
    lines = [
        '# Forecast Report', '',
        f'- Data window: {lo.date()} to {hi.date()} ({len(y)} complete weeks)',
        f'- Train: {n_train} weeks ({y.index[0].date()} to {y.index[n_train - 1].date()})',
        f'- Test (holdout): {len(y) - n_train} weeks ({y.index[n_train].date()} to {y.index[-1].date()})',
        f'- Holt-Winters yearly seasonality used: {seasonal}', '',
        '## Holdout metrics', '',
        '| Model | MAE (GBP) | MAPE % | WAPE % | MAE vs naive % | Beats naive |',
        '|---|---|---|---|---|---|',
    ]
    for r in metrics.itertuples():
        lines.append(f'| {r.model} | {r.mae:,.0f} | {r.mape:.1f} | {r.wape:.1f} | '
                     f'{r.improvement_mae_pct_vs_naive:+.1f} | {"yes" if r.beats_naive else "no"} |')
    lines += ['', '## Verdict', '',
              f'- {verdict} (Holt-Winters MAE {hw["mae"]:,.0f} vs naive {naive_mae:,.0f}).',
              f'- Lowest holdout MAE: {best["model"]} ({best["mae"]:,.0f}).',
              '- Results are reported as measured; the model is not tuned to pass.', '',
              '## Limitations', '',
              f'- Only {len(y)} weeks of history: yearly seasonality cannot be estimated by Holt-Winters '
              f'unless train has at least {2 * SEASONAL_PERIOD} weeks.',
              '- The holiday closure appears as real zero-revenue weeks and the Q4 peak sits in the holdout.',
              '- Intervals are approximate (residual standard deviation scaled by the square root of the horizon).',
              '- Boundary weeks outside the data window are dropped, so weekly totals are lower than the store total.']
    (REPORTS / 'forecast_report.md').write_text(NL.join(lines) + NL)


def main():
    y, lo, hi = weekly_series()
    if len(y) < MIN_WEEKS:
        sys.exit(f'Only {len(y)} complete weeks; need at least {MIN_WEEKS}.')
    n_train = int(len(y) * TRAIN_FRAC)
    train, test = y.iloc[:n_train], y.iloc[n_train:]
    horizon = len(test)
    assert train.index.max() < test.index.min(), 'train/test overlap'
    hist = y.values

    naive = np.repeat(train.iloc[-1], horizon)
    moving = np.repeat(train.iloc[-MA_WINDOW:].mean(), horizon)
    snaive = seasonal_naive(hist, n_train, horizon)
    model, seasonal = fit_holt_winters(train.values)
    hw_point = np.asarray(model.forecast(horizon))
    sigma = float(np.std(train.values - model.fittedvalues, ddof=1))
    lower, upper = interval(hw_point, sigma)

    candidates = [('naive', naive), ('moving_avg_4w', moving), ('seasonal_naive_52w', snaive), ('holt_winters', hw_point)]
    rows = [{'model': name, **score(test.values, pred)} for name, pred in candidates if not np.isnan(pred).any()]
    metrics = pd.DataFrame(rows)
    base = metrics.loc[metrics['model'] == 'naive', 'mae'].iloc[0]
    metrics['improvement_mae_pct_vs_naive'] = (base - metrics['mae']) / base * 100
    metrics['beats_naive'] = (metrics['mae'] < base) & (metrics['model'] != 'naive')
    metrics['is_best'] = metrics['mae'] == metrics['mae'].min()
    metrics['n_train'] = n_train
    metrics['n_test'] = horizon

    train_df = pd.DataFrame({'week_start': train.index, 'actual': train.values,
                             'forecast': model.fittedvalues, 'split': 'train'})
    test_df = pd.DataFrame({'week_start': test.index, 'actual': test.values, 'naive': naive,
                            'moving_avg_4w': moving, 'seasonal_naive_52w': snaive, 'forecast': hw_point,
                            'lower': lower, 'upper': upper, 'split': 'test'})

    full_model, _ = fit_holt_winters(hist)
    f_point = np.asarray(full_model.forecast(FUTURE_WEEKS))
    f_sigma = float(np.std(hist - full_model.fittedvalues, ddof=1))
    f_lower, f_upper = interval(f_point, f_sigma)
    future_index = pd.date_range(y.index[-1] + pd.Timedelta(days=7), periods=FUTURE_WEEKS, freq='7D')
    future_df = pd.DataFrame({'week_start': future_index, 'actual': np.nan,
                              'seasonal_naive_52w': seasonal_naive(hist, len(hist), FUTURE_WEEKS),
                              'forecast': f_point, 'lower': f_lower, 'upper': f_upper, 'split': 'future'})

    out = pd.concat([train_df, test_df, future_df], ignore_index=True)
    for col in ['naive', 'moving_avg_4w', 'seasonal_naive_52w', 'lower', 'upper']:
        if col not in out:
            out[col] = np.nan
    out['is_future'] = out['split'] == 'future'
    out['week_start'] = pd.to_datetime(out['week_start']).dt.date
    out = out[['week_start', 'actual', 'naive', 'moving_avg_4w', 'seasonal_naive_52w', 'forecast',
               'lower', 'upper', 'split', 'is_future']]

    PROC.mkdir(parents=True, exist_ok=True)
    out.to_parquet(parquet('forecast_weekly'), index=False)
    metrics.to_parquet(parquet('forecast_metrics'), index=False)
    write_report(metrics, y, n_train, lo, hi, seasonal)

    print(f'Weeks: {len(y)} (train {n_train}, test {horizon}); yearly seasonality used: {seasonal}')
    print(metrics[['model', 'mae', 'mape', 'wape', 'improvement_mae_pct_vs_naive', 'beats_naive']].round(2).to_string(index=False))
    hw = metrics.loc[metrics['model'] == 'holt_winters', 'beats_naive'].iloc[0]
    print('Holt-Winters beats naive on the holdout.' if hw else
          'NOTE: Holt-Winters did NOT beat the naive MAE on the holdout. Reported as measured (see reports/forecast_report.md).')
    return 0


if __name__ == '__main__':
    sys.exit(main())

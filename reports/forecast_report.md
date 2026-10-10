# Forecast Report

- Data window: 2009-12-01 to 2011-12-09 (104 complete weeks)
- Train: 83 weeks (2009-12-07 to 2011-07-04)
- Test (holdout): 21 weeks (2011-07-11 to 2011-11-28)
- Holt-Winters yearly seasonality used: False

## Holdout metrics

| Model | MAE (GBP) | MAPE % | WAPE % | MAE vs naive % | Beats naive |
|---|---|---|---|---|---|
| naive | 69,840 | 25.9 | 30.1 | +0.0 | no |
| moving_avg_4w | 82,880 | 30.2 | 35.8 | -18.7 | no |
| seasonal_naive_52w | 34,141 | 15.8 | 14.7 | +51.1 | yes |
| holt_winters | 73,319 | 27.0 | 31.6 | -5.0 | no |

## Verdict

- Holt-Winters does NOT beat the naive baseline (Holt-Winters MAE 73,319 vs naive 69,840).
- Lowest holdout MAE: seasonal_naive_52w (34,141).
- Results are reported as measured; the model is not tuned to pass.

## Limitations

- Only 104 weeks of history: yearly seasonality cannot be estimated by Holt-Winters unless train has at least 104 weeks.
- The holiday closure appears as real zero-revenue weeks and the Q4 peak sits in the holdout.
- Intervals are approximate (residual standard deviation scaled by the square root of the horizon).
- Boundary weeks outside the data window are dropped, so weekly totals are lower than the store total.

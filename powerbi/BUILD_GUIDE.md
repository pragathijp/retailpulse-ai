# Power BI Build Guide (Phase 6, Path A)

Goal: a report whose KPI cards equal the metrics contract within 0.01 GBP, verified by `python run.py audit`.
Power BI Desktop is required (Windows). Everything below is manual in Power BI; the DAX is ready to paste.

## 0. Prepare the data
```powershell
python run.py run_all --skip-ingest
```
Confirm `data\processed\` contains: `fact_sales`, `dim_date`, `mart_monthly_sales`, `mart_product_performance`,
`mart_customer_rfm`, `audit_revenue_variance`, `forecast_weekly`, `forecast_metrics` (all `.parquet`).

## 1. Load the Parquet files
Home > Get data > Parquet. Load all eight files from `D:\retailpulse-ai\data\processed\`. In Power Query make no filters.
Set these column types (Transform data):

| Table | Columns | Type |
|---|---|---|
| fact_sales | `gross_sales`, `return_amount`, `net_revenue_line`, `unit_price` | Fixed decimal number |
| fact_sales | `invoice_date`, `sales_month` | Date |
| fact_sales | `is_valid_sale`, `is_return`, `is_non_product` | True/False |
| dim_date | `date_key`, `month_start`, `week_start` | Date |
| mart_monthly_sales | `sales_month` | Date; money columns Fixed decimal number |
| mart_customer_rfm | `monetary_raw`, `monetary` | Fixed decimal number |
| forecast_weekly | `week_start` | Date |

## 2. Calculated tables (Modeling > New table)
```
dim_month = SUMMARIZE(dim_date, dim_date[month_start], dim_date[year_month])
dim_country = DISTINCT(fact_sales[country])
```

## 3. Relationships (Model view; single direction, one-to-many)
| One side | Many side |
|---|---|
| `dim_date[date_key]` | `fact_sales[invoice_date]` |
| `dim_country[country]` | `fact_sales[country]` |
| `dim_country[country]` | `mart_monthly_sales[country]` |
| `dim_month[month_start]` | `mart_monthly_sales[sales_month]` |
| `mart_product_performance[stock_code]` | `fact_sales[stock_code]` |

Leave `mart_customer_rfm`, `audit_revenue_variance`, `forecast_weekly` and `forecast_metrics` unrelated.
Mark `dim_date` as the date table (Table tools > Mark as date table > `date_key`).

## 4. Measures
Enter Data > one column table named `_Measures`. Add every measure in `powerbi/measures.dax` (Modeling > New measure).
Names must match exactly; the first six are the contract metrics.

## 5. Report pages
| Page | Visuals |
|---|---|
| Overview | Cards: Net Revenue, Gross Revenue, Return Value, Orders, Units Sold, AOV, Return Rate. Line and clustered column: axis `dim_date[year_month]`, column `Orders`, line `Net Revenue`. Table: `year_month`, `Net Revenue`, `Net Revenue MoM %`. Slicers: `dim_date[date_key]` (between), `dim_country[country]`. |
| Products | Bar: top 10 `mart_product_performance[description]` by `Net Revenue` (Top N filter). Bar: bottom 10 by `Units Sold`. Line: `pareto_rank` vs `cumulative_share`. Cards: `Ranked SKUs`, `SKUs for 80 Percent`, `Pareto Density %`. |
| Geography | Map or horizontal bar: `dim_country[country]` by `Net Revenue`; a second bar with a visual filter `country is not United Kingdom`. |
| Customers | Cards: `RFM Customers`, `RFM Net Revenue`, `Revenue Variance`, `Unexplained Variance`. Bar: customers by `segment`. Matrix: `r_score` rows, `f_score` columns, count of `customer_id`. Text box: customers without an ID are excluded here by design. |
| Forecast | Line: `forecast_weekly[week_start]` with `actual`, `forecast`, `seasonal_naive_52w`, `naive`. Table from `forecast_metrics` (model, mae, mape, wape, beats_naive). Cards: `Best Forecast Model`, `Best Model MAE`, `Holt-Winters MAE`, `Naive MAE`. |

## 6. Export the KPIs for the audit
Follow `powerbi/kpi_export.dax` (Option A needs no extra tools). Save as `data\bi_exports\pbi_kpis.csv`.
Check the Overview cards with no slicer applied match the export.

## 7. Verify
```powershell
python run.py audit
```
`test_powerbi_kpis_match_contract` must show PASSED (not SKIPPED). If it fails, the message names the metric and both values.
Common causes: a slicer was applied during export, a column was left as Decimal number and displays rounded, or a
measure was edited so it no longer equals the contract.

## 8. Save and commit
Save as `reports\retailpulse.pbix`. The `.pbix` is git-ignored because it embeds about 1M rows; commit screenshots of
the five pages to `docs\powerbi\` and keep `powerbi\measures.dax` (the source of truth for the measures) in git.

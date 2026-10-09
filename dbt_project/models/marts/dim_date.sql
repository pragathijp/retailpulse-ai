{{ config(materialized='external', location=var('processed_dir') ~ '/dim_date.parquet', format='parquet') }}

with bounds as (
    select min(invoice_date) as min_d, max(invoice_date) as max_d
    from {{ ref('int_transactions_cleaned') }}
),
days as (
    select cast(unnest(generate_series(min_d, max_d, interval 1 day)) as date) as date_key
    from bounds
)
select
    date_key,
    year(date_key) as year,
    month(date_key) as month_num,
    strftime(date_key, '%Y-%m') as year_month,
    cast(date_trunc('month', date_key) as date) as month_start,
    cast(date_trunc('week', date_key) as date) as week_start,
    dayofweek(date_key) as day_of_week
from days
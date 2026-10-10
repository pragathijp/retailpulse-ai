{{ config(materialized='table') }}

-- Row-count ledger from raw to staged, plus headline data-quality counts.
with src as (
    select * from {{ source('raw', 'retail_transactions') }}
),
raw_valid as (
    select * from src
    where invoice_ts is not null and quantity is not null and unit_price is not null
),
distinct_valid as (
    select distinct invoice_no, stock_code, description, quantity, invoice_ts, unit_price, customer_id, country
    from raw_valid
)
select 'raw_rows' as check_name, cast(count(*) as decimal(38,4)) as check_value from src
union all select 'invalid_rows_dropped',
    cast((select count(*) from src) - (select count(*) from raw_valid) as decimal(38,4))
union all select 'exact_duplicates_removed',
{% if var('dedupe_exact_rows', true) %}
    cast((select count(*) from raw_valid) - (select count(*) from distinct_valid) as decimal(38,4))
{% else %}
    cast(0 as decimal(38,4))
{% endif %}
union all select 'staged_rows', cast(count(*) as decimal(38,4)) from {{ ref('stg_retail_transactions') }}
union all select 'line_key_collisions_resolved', cast(count(*) as decimal(38,4)) from {{ ref('stg_retail_transactions') }} where line_seq > 1
union all select 'valid_sale_rows', cast(count(*) as decimal(38,4)) from {{ ref('int_transactions_cleaned') }} where is_valid_sale
union all select 'return_rows', cast(count(*) as decimal(38,4)) from {{ ref('int_transactions_cleaned') }} where is_return
union all select 'non_product_rows', cast(count(*) as decimal(38,4)) from {{ ref('int_transactions_cleaned') }} where is_non_product
union all select 'zero_or_negative_price_rows', cast(count(*) as decimal(38,4)) from {{ ref('int_transactions_cleaned') }} where is_adjustment
union all select 'null_customer_rows', cast(count(*) as decimal(38,4)) from {{ ref('int_transactions_cleaned') }} where customer_id is null
union all select 'null_customer_net_revenue',
    cast(coalesce(sum(net_revenue_line), 0) as decimal(38,4)) from {{ ref('int_transactions_cleaned') }} where customer_id is null

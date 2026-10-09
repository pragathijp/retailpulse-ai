{{ config(materialized='view') }}

with src as (
    select
        nullif(trim(invoice_no), '') as invoice_no,
        nullif(trim(stock_code), '') as stock_code,
        nullif(trim(description), '') as description,
        cast(quantity as integer) as quantity,
        cast(invoice_ts as timestamp) as invoice_ts,
        cast(unit_price as decimal(18,4)) as unit_price,
        nullif(trim(customer_id), '') as customer_id,
        coalesce(nullif(trim(country), ''), 'Unknown') as country
    from {{ source('raw', 'retail_transactions') }}
    where invoice_ts is not null
      and quantity is not null
      and unit_price is not null
),

keyed as (
    select
        *,
        cast(invoice_ts as date) as invoice_date,
        md5(concat(
            coalesce(invoice_no, ''), '_',
            coalesce(stock_code, ''), '_',
            cast(invoice_ts as varchar), '_',
            cast(quantity as varchar)
        )) as transaction_line_key
    from src
),

ranked as (
    select
        *,
        row_number() over (
            partition by transaction_line_key, unit_price, customer_id, country, description
            order by unit_price, customer_id
        ) as dup_rank
    from keyed
)

select
    transaction_line_key, invoice_no, stock_code, description, quantity,
    invoice_ts, invoice_date, unit_price, customer_id, country, dup_rank
from ranked
{% if var('dedupe_exact_rows', true) %}
where dup_rank = 1
{% endif %}
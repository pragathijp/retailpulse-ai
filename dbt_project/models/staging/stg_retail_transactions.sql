{{ config(materialized='view') }}

-- Surrogate key design:
--   base key  = md5(invoice_no, stock_code, invoice_ts, quantity)     (PRD formula, not unique on its own)
--   line_seq  = position among rows sharing a base key after exact duplicates are removed
--   final key = md5(base key, '_', line_seq)                          (unique and deterministic)
-- Rows that share a base key but differ in price, customer, country or description are real, separate lines.

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
        )) as base_line_key
    from src
),

ranked as (
    select
        *,
        row_number() over (
            partition by base_line_key, unit_price, customer_id, country, description
            order by unit_price, customer_id
        ) as dup_rank
    from keyed
),

deduped as (
    select * from ranked
    {% if var('dedupe_exact_rows', true) %}
    where dup_rank = 1
    {% endif %}
),

sequenced as (
    select
        *,
        row_number() over (
            partition by base_line_key
            order by unit_price, customer_id, country, description, dup_rank
        ) as line_seq
    from deduped
)

select
    md5(concat(base_line_key, '_', cast(line_seq as varchar))) as transaction_line_key,
    invoice_no, stock_code, description, quantity,
    invoice_ts, invoice_date, unit_price, customer_id, country,
    dup_rank, line_seq
from sequenced

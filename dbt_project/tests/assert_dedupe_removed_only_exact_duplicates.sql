-- Staged rows must equal the number of distinct full rows in the raw table
-- (dedupe removes exact duplicates only).
{% if var('dedupe_exact_rows', true) %}
select 'mismatch' as failure
from (
    select
        (select count(*) from {{ ref('stg_retail_transactions') }}) as staged_rows,
        (select count(*) from (
            select distinct invoice_no, stock_code, description, quantity, invoice_ts, unit_price, customer_id, country
            from {{ source('raw', 'retail_transactions') }}
            where invoice_ts is not null and quantity is not null and unit_price is not null
        )) as distinct_raw_rows
)
where staged_rows <> distinct_raw_rows
{% else %}
select 1 as failure where false
{% endif %}

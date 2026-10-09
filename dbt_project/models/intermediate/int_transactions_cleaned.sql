{{ config(materialized='table') }}

with base as (
    select
        s.transaction_line_key, s.invoice_no, s.stock_code, s.description,
        s.quantity, s.invoice_ts, s.invoice_date, s.unit_price, s.customer_id, s.country,
        coalesce(s.invoice_no like 'C%', false) or s.quantity < 0 as is_return,
        (np.stock_code is not null) as is_non_product
    from {{ ref('stg_retail_transactions') }} s
    left join {{ ref('non_product_codes') }} np
        on upper(s.stock_code) = upper(np.stock_code)
),

flagged as (
    select
        *,
        (not is_return and quantity > 0 and unit_price > 0) as is_valid_sale,
        (unit_price <= 0) as is_adjustment
    from base
),

amounts as (
    select
        *,
        cast(case when is_valid_sale then quantity * unit_price else 0 end as decimal(18,4)) as gross_sales,
        cast(case when is_return and unit_price > 0 then abs(quantity) * unit_price else 0 end as decimal(18,4)) as return_amount
    from flagged
)

select
    transaction_line_key, invoice_no, stock_code, description, quantity,
    invoice_ts, invoice_date,
    cast(date_trunc('month', invoice_date) as date) as sales_month,
    unit_price, customer_id, country,
    is_return, is_non_product, is_valid_sale, is_adjustment,
    gross_sales, return_amount,
    cast(gross_sales - return_amount as decimal(18,4)) as net_revenue_line
from amounts
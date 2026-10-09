{{ config(materialized='external', location=var('processed_dir') ~ '/fact_sales.parquet', format='parquet') }}

select
    transaction_line_key, invoice_no, stock_code, description, quantity,
    invoice_ts, invoice_date, sales_month, unit_price, customer_id, country,
    is_return, is_non_product, is_valid_sale, is_adjustment,
    gross_sales, return_amount, net_revenue_line
from {{ ref('int_transactions_cleaned') }}
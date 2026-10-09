with staging as (
    select * from {{ ref('stg_retail_transactions') }}
),

order_aggregated as (
    select
        invoice_no,
        customer_id,
        country,
        min(invoice_ts) as order_ts,
        count(distinct stock_code) as total_unique_items,
        sum(quantity) as total_quantity,
        sum(case when not is_cancellation and unit_price > 0 then gross_revenue else 0 end) as gross_revenue,
        sum(gross_revenue) as net_revenue,
        max(is_cancellation) as is_cancelled
    from staging
    group by
        invoice_no,
        customer_id,
        country
)

select * from order_aggregated

with orders as (
    select * from {{ ref('int_orders') }}
),

customer_agg as (
    select
        customer_id,
        min(order_ts) as first_order_ts,
        max(order_ts) as most_recent_order_ts,
        count(distinct invoice_no) as total_orders,
        sum(case when not is_cancelled then net_revenue else 0 end) as lifetime_monetary_value,
        max(country) as primary_country
    from orders
    where customer_id is not null
    group by customer_id
)

select * from customer_agg

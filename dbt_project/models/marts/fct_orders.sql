with orders as (
    select * from {{ ref('int_orders') }}
)

select
    invoice_no,
    customer_id,
    country,
    order_ts,
    total_unique_items,
    total_quantity,
    gross_revenue,
    net_revenue,
    is_cancelled
from orders

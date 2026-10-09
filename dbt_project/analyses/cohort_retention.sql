with customer_first_purchase as (
    select
        customer_id,
        date_trunc('month', min(invoice_ts)) as cohort_month
    from {{ ref('fact_sales') }}
    where customer_id is not null and is_valid_sale
    group by 1
),
customer_activity as (
    select distinct
        f.customer_id,
        c.cohort_month,
        date_trunc('month', f.invoice_ts) as activity_month,
        datediff('month', c.cohort_month, date_trunc('month', f.invoice_ts)) as month_offset
    from {{ ref('fact_sales') }} f
    join customer_first_purchase c on f.customer_id = c.customer_id
    where f.is_valid_sale
)
select
    cohort_month,
    month_offset,
    count(distinct customer_id) as active_customers
from customer_activity
group by 1, 2
order by cohort_month, month_offset;
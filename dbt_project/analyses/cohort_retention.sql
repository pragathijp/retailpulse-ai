-- Customer cohort retention, months 0 to 12. Customers without an ID are excluded.
with purchases as (
    select distinct customer_id, sales_month
    from {{ ref('fact_sales') }}
    where is_valid_sale and customer_id is not null
),
cohorts as (
    select customer_id, min(sales_month) as cohort_month
    from purchases
    group by customer_id
),
sizes as (
    select cohort_month, count(*) as cohort_size
    from cohorts
    group by cohort_month
),
activity as (
    select
        c.cohort_month,
        date_diff('month', c.cohort_month, p.sales_month) as month_offset,
        count(distinct p.customer_id) as active_customers
    from cohorts c
    join purchases p on p.customer_id = c.customer_id
    group by 1, 2
)
select
    a.cohort_month,
    a.month_offset,
    s.cohort_size,
    a.active_customers,
    cast(a.active_customers * 1.0 / s.cohort_size as decimal(8,4)) as retention_rate
from activity a
join sizes s on s.cohort_month = a.cohort_month
where a.month_offset between 0 and 12
order by a.cohort_month, a.month_offset

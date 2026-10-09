{{ config(materialized='external', location=var('processed_dir') ~ '/mart_monthly_sales.parquet', format='parquet') }}

with bounds as (
    select min(invoice_date) as min_d, max(invoice_date) as max_d
    from {{ ref('int_transactions_cleaned') }}
),
agg as (
    select
        sales_month,
        country,
        sum(gross_sales) as gross_sales,
        sum(return_amount) as return_amount,
        sum(net_revenue_line) as net_revenue,
        count(distinct case when is_valid_sale then invoice_no end) as order_count,
        sum(case when is_valid_sale then quantity else 0 end) as units_sold,
        count(distinct case when is_return then invoice_no end) as return_invoice_count
    from {{ ref('int_transactions_cleaned') }}
    group by sales_month, country
),
flagged as (
    select
        a.*,
        (b.min_d > a.sales_month or b.max_d < cast(a.sales_month + interval 1 month - interval 1 day as date)) as is_partial_month,
        lag(a.sales_month) over (partition by a.country order by a.sales_month) as prev_month,
        lag(a.net_revenue) over (partition by a.country order by a.sales_month) as prev_net_revenue
    from agg a
    cross join bounds b
)
select
    sales_month, country, gross_sales, return_amount, net_revenue, order_count, units_sold, return_invoice_count,
    cast(gross_sales / nullif(order_count, 0) as decimal(18,4)) as aov,
    is_partial_month,
    case
        when is_partial_month then null
        when prev_month is null then null
        when prev_month <> cast(sales_month - interval 1 month as date) then null
        else cast((net_revenue - prev_net_revenue) / nullif(prev_net_revenue, 0) as decimal(18,6))
    end as mom_growth_pct
from flagged
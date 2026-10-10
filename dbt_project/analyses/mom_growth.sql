-- Store-level month-over-month net revenue growth. Partial months are suppressed.
with m as (
    select sales_month, sum(net_revenue) as net_revenue, bool_or(is_partial_month) as is_partial
    from {{ ref('mart_monthly_sales') }}
    group by sales_month
)
select
    sales_month,
    net_revenue,
    lag(net_revenue) over (order by sales_month) as prev_net_revenue,
    case when is_partial then null
         else cast(100.0 * (net_revenue - lag(net_revenue) over (order by sales_month))
              / nullif(lag(net_revenue) over (order by sales_month), 0) as decimal(10,2))
    end as mom_pct,
    is_partial
from m
order by sales_month

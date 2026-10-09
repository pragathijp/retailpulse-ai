select
    sales_month,
    country,
    net_revenue,
    lag(net_revenue) over (partition by country order by sales_month) as prev_month_net_revenue,
    case 
        when is_partial_month then null
        else round(((net_revenue - lag(net_revenue) over (partition by country order by sales_month)) / nullif(lag(net_revenue) over (partition by country order by sales_month), 0)) * 100, 2)
    end as mom_growth_pct
from {{ ref('mart_monthly_sales') }}
order by country, sales_month;
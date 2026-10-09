select 'mismatch' as failure
from (
    select (select sum(net_revenue) from {{ ref('mart_monthly_sales') }}) as m,
           (select sum(net_revenue_line) from {{ ref('fact_sales') }}) as f
)
where abs(m - f) > 0.01
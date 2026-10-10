-- Fails on any full (non-partial) month whose store-level net revenue is negative.
select sales_month, sum(net_revenue) as net_revenue
from {{ ref('mart_monthly_sales') }}
where not is_partial_month
group by sales_month
having sum(net_revenue) < 0

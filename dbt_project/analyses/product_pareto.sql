select
    stock_code,
    description,
    net_revenue,
    pareto_rank,
    cumulative_share,
    is_top_80
from {{ ref('mart_product_performance') }}
order by pareto_rank;
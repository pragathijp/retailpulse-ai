select
    stock_code,
    description,
    net_revenue,
    units_sold,
    return_rate
from {{ ref('mart_product_performance') }}
order by return_rate desc;
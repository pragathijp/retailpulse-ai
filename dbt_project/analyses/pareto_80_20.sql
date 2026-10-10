-- How many SKUs produce 80 percent of positive net revenue (non-product codes excluded).
select
    count(*) filter (where is_top_80)                                                  as skus_for_80_pct_revenue,
    count(*)                                                                           as ranked_skus,
    cast(100.0 * count(*) filter (where is_top_80) / count(*) as decimal(10,2))        as pct_of_skus
from {{ ref('mart_product_performance') }}
where pareto_rank is not null

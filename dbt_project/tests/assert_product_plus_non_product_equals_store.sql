-- Product-level net revenue plus non-product (postage, fees) net revenue must equal the store total.
select 'mismatch' as failure
from (
    select
        (select coalesce(sum(net_revenue), 0) from {{ ref('mart_product_performance') }}) as product_net,
        (select coalesce(sum(net_revenue_line), 0) from {{ ref('fact_sales') }} where is_non_product) as non_product_net,
        (select sum(net_revenue_line) from {{ ref('fact_sales') }}) as store_net
)
where abs(product_net + non_product_net - store_net) > 0.01

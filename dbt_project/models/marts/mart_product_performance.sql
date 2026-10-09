{{ config(materialized='external', location=var('processed_dir') ~ '/mart_product_performance.parquet', format='parquet') }}

with agg as (
    select
        stock_code,
        mode(description) as description,
        sum(gross_sales) as gross_sales,
        sum(return_amount) as return_amount,
        sum(net_revenue_line) as net_revenue,
        sum(case when is_valid_sale then quantity else 0 end) as units_sold,
        sum(case when is_return then abs(quantity) else 0 end) as units_returned,
        count(distinct case when is_valid_sale then invoice_no end) as order_count
    from {{ ref('int_transactions_cleaned') }}
    where not is_non_product and stock_code is not null
    group by stock_code
),
positive as (
    select stock_code, net_revenue, sum(net_revenue) over () as total_positive
    from agg where net_revenue > 0
),
pareto as (
    select
        stock_code, total_positive,
        row_number() over (order by net_revenue desc, stock_code) as pareto_rank,
        sum(net_revenue) over (order by net_revenue desc, stock_code rows between unbounded preceding and current row) as cumulative_net_revenue
    from positive
)
select
    a.stock_code, a.description, a.gross_sales, a.return_amount, a.net_revenue, a.units_sold, a.units_returned, a.order_count,
    cast(a.return_amount / nullif(a.gross_sales, 0) as decimal(18,6)) as return_rate,
    p.pareto_rank, p.cumulative_net_revenue,
    cast(p.cumulative_net_revenue / p.total_positive as decimal(18,6)) as cumulative_share,
    coalesce((p.cumulative_net_revenue - a.net_revenue) / p.total_positive < 0.8, false) as is_top_80
from agg a
left join pareto p on a.stock_code = p.stock_code
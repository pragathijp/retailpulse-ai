select 'mismatch' as failure
from (
    select sum(gross_sales) - sum(return_amount) as expected,
           sum(net_revenue_line) as actual
    from {{ ref('fact_sales') }}
)
where abs(expected - actual) > 0.01
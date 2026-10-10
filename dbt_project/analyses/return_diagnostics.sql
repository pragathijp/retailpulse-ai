-- Top 20 products by value returned (non-product codes excluded).
select stock_code, description, units_returned, return_amount, gross_sales, return_rate
from {{ ref('mart_product_performance') }}
order by return_amount desc
limit 20

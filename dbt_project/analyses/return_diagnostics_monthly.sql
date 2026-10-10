-- Return value and rate by month and country (partial months excluded).
select
    sales_month,
    country,
    return_amount,
    gross_sales,
    cast(return_amount / nullif(gross_sales, 0) as decimal(10,4)) as return_rate,
    return_invoice_count
from {{ ref('mart_monthly_sales') }}
where not is_partial_month
order by sales_month, country

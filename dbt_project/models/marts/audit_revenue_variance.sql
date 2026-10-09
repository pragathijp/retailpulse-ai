{{ config(materialized='external', location=var('processed_dir') ~ '/audit_revenue_variance.parquet', format='parquet') }}

with store as (
    select
        sum(net_revenue_line) as total_store_net_revenue,
        count(case when customer_id is null then 1 end) as unattributed_rows,
        count(distinct case when customer_id is null then invoice_no end) as unattributed_invoices,
        coalesce(sum(case when customer_id is null then net_revenue_line end), 0) as unattributed_net_revenue
    from {{ ref('int_transactions_cleaned') }}
),
rfm as (
    select sum(monetary_raw) as total_rfm_net_revenue, count(*) as rfm_customers
    from {{ ref('mart_customer_rfm') }}
),
ineligible as (
    select coalesce(sum(net_revenue_line), 0) as ineligible_customer_net_revenue
    from {{ ref('int_transactions_cleaned') }}
    where customer_id is not null
      and customer_id not in (select customer_id from {{ ref('mart_customer_rfm') }})
)
select
    current_timestamp as run_ts,
    s.total_store_net_revenue,
    r.total_rfm_net_revenue,
    r.rfm_customers,
    s.total_store_net_revenue - r.total_rfm_net_revenue as delta_revenue,
    cast((s.total_store_net_revenue - r.total_rfm_net_revenue) / nullif(s.total_store_net_revenue, 0) as decimal(18,6)) as delta_pct,
    s.unattributed_rows,
    s.unattributed_invoices,
    s.unattributed_net_revenue,
    i.ineligible_customer_net_revenue,
    s.total_store_net_revenue - r.total_rfm_net_revenue - s.unattributed_net_revenue - i.ineligible_customer_net_revenue as unexplained_revenue
from store s
cross join rfm r
cross join ineligible i
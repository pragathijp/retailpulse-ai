{{ config(materialized='external', location=var('processed_dir') ~ '/mart_customer_rfm.parquet', format='parquet') }}

with ref_date as (
    select max(invoice_date) + {{ var('rfm_reference_date_offset_days') }} as ref_date
    from {{ ref('int_transactions_cleaned') }}
),
cust as (
    select
        customer_id,
        max(case when is_valid_sale then invoice_date end) as last_purchase_date,
        count(distinct case when is_valid_sale then invoice_no end) as frequency,
        sum(net_revenue_line) as monetary_raw
    from {{ ref('int_transactions_cleaned') }}
    where customer_id is not null
    group by customer_id
    having count(case when is_valid_sale then 1 end) > 0
),
metrics as (
    select
        c.customer_id, c.last_purchase_date,
        date_diff('day', c.last_purchase_date, r.ref_date) as recency_days,
        c.frequency, c.monetary_raw,
        greatest(c.monetary_raw, 0) as monetary
    from cust c cross join ref_date r
),
scored as (
    select
        *,
        ntile(5) over (order by recency_days desc, customer_id) as r_score,
        ntile(5) over (order by frequency, customer_id) as f_score,
        ntile(5) over (order by monetary, customer_id) as m_score
    from metrics
)
select
    s.customer_id, s.last_purchase_date, s.recency_days, s.frequency, s.monetary_raw, s.monetary,
    s.r_score, s.f_score, s.m_score,
    cast(s.r_score as varchar) || cast(s.f_score as varchar) || cast(s.m_score as varchar) as rfm_score,
    m.segment
from scored s
join {{ ref('rfm_segment_map') }} m
  on s.r_score between m.r_min and m.r_max
 and s.f_score between m.f_min and m.f_max
 and s.m_score between m.m_min and m.m_max
qualify row_number() over (partition by s.customer_id order by m.priority) = 1
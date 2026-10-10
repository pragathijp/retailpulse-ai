-- customer_id must never carry the float artefact (17850.0) or a nan token.
select customer_id
from {{ ref('fact_sales') }}
where customer_id like '%.0'
   or lower(customer_id) in ('nan', 'none', 'null', '')

-- RFM may only contain identified customers.
select 1 as failure
from {{ ref('mart_customer_rfm') }}
where customer_id is null

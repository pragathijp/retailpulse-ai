select 'mismatch' as failure
from {{ ref('audit_revenue_variance') }}
where abs(unexplained_revenue) > 0.01
   or abs(delta_revenue - unattributed_net_revenue - ineligible_customer_net_revenue) > 0.01
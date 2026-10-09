select transaction_line_key
from {{ ref('int_transactions_cleaned') }}
where (is_valid_sale and is_return)
   or (is_return and gross_sales <> 0)
   or (is_valid_sale and return_amount <> 0)
   or (gross_sales > 0 and return_amount > 0)
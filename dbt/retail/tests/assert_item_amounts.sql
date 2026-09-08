select order_line_id
from {{ ref('fct_order_items') }}
where quantity <= 0 or unit_price < 0
   or abs(line_amount - quantity * unit_price) > 0.01

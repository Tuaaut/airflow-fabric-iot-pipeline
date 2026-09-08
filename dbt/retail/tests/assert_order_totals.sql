select order_id
from {{ ref('fct_orders') }}
where abs(order_amount - item_subtotal) > 0.01
   or total_paid_amount < 0
   or total_paid_amount > order_amount
   or (order_status = 'completed' and abs(total_paid_amount - order_amount) > 0.01)
   or (order_status in ('pending', 'cancelled') and total_paid_amount <> 0)

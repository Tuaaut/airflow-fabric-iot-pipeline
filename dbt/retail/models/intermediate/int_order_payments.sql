{{ config(materialized='view') }}

-- Roll up payment facts so there is one payment summary row per order.
select
  order_id,
  sum(case when payment_status = 'paid' then payment_amount else 0 end) as total_paid_amount,
  count(case when payment_status = 'paid' then 1 end) as successful_payment_count,
  max(payment_date) as latest_payment_date
from {{ ref('stg_payments') }}
group by order_id

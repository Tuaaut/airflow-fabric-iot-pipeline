{{ config(materialized='view') }}

-- Cast order totals and normalize status values at the order grain.
select
  order_id,
  customer_id,
  store_id,
  order_date,
  cast(order_amount as decimal(12,2)) as order_amount,
  lower(order_status) as order_status
from {{ ref('raw_orders') }}

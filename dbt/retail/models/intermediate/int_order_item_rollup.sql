{{ config(materialized='view') }}

-- Summarize item-level activity back to the order grain.
select
  order_id,
  sum(quantity) as total_quantity,
  count(distinct product_id) as distinct_products,
  cast(sum(line_amount) as decimal(12,2)) as item_subtotal
from {{ ref('stg_order_items') }}
group by order_id

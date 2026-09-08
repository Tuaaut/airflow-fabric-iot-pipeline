{{ config(materialized='view') }}

-- Enrich each order line with its order context and product attributes.
select
  oi.order_line_id,
  oi.order_id,
  o.customer_id,
  o.store_id,
  o.order_date,
  o.order_status,
  oi.product_id,
  p.product_name,
  p.category,
  p.brand,
  oi.quantity,
  oi.unit_price,
  oi.line_amount
from {{ ref('stg_order_items') }} oi
left join {{ ref('stg_orders') }} o
  on oi.order_id = o.order_id
left join {{ ref('stg_products') }} p
  on oi.product_id = p.product_id

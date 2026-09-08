{{ config(materialized='table') }}

-- Keep one row per order line for product-level retail analysis.
select
  i.order_line_id,
  i.order_id,
  i.customer_id,
  i.store_id,
  i.product_id,
  i.order_date,
  i.order_status,
  c.customer_name,
  c.city as customer_city,
  s.store_name,
  s.city as store_city,
  s.region as store_region,
  p.product_name,
  p.category,
  p.brand,
  i.quantity,
  i.unit_price,
  i.line_amount
from {{ ref('int_order_item_enriched') }} i
left join {{ ref('stg_customers') }} c
  on i.customer_id = c.customer_id
left join {{ ref('stg_stores') }} s
  on i.store_id = s.store_id
left join {{ ref('stg_products') }} p
  on i.product_id = p.product_id

{{ config(materialized='table') }}

-- Build one row per product with sales history from item-level facts.
select
  p.product_id,
  p.product_name,
  p.category,
  p.brand,
  p.base_price,
  coalesce(sum(i.quantity), 0) as total_quantity_sold,
  coalesce(sum(i.line_amount), 0) as total_sales_amount,
  min(i.order_date) as first_order_date,
  max(i.order_date) as latest_order_date
from {{ ref('stg_products') }} p
left join {{ ref('int_order_item_enriched') }} i
  on p.product_id = i.product_id
group by
  p.product_id,
  p.product_name,
  p.category,
  p.brand,
  p.base_price

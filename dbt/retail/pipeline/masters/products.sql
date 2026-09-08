{{ config(materialized='table') }}

-- Generate product master data for item-level retail analysis.
with base as (
  select i as product_id
  from range(1001, 1061) as t(i)
)

select
  product_id,
  case ((product_id - 1001) % 5)
    when 0 then 'beverage'
    when 1 then 'snack'
    when 2 then 'personal_care'
    when 3 then 'household'
    else 'dairy'
  end as category,
  case ((product_id - 1001) % 4)
    when 0 then 'brand_a'
    when 1 then 'brand_b'
    when 2 then 'brand_c'
    else 'brand_d'
  end as brand,
  'product_' || lpad(cast(product_id as varchar), 4, '0') as product_name,
  cast(
    35
    + (((product_id - 1001) % 10) * 12)
    + (((product_id - 1001) % 3) * 5)
    as decimal(10,2)
  ) as base_price
from base

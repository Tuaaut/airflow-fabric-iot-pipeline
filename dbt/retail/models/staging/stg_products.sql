{{ config(materialized='view') }}

-- Standardize product text and numeric attributes for item-level analysis.
select
  product_id,
  upper(product_name) as product_name,
  lower(category) as category,
  lower(brand) as brand,
  cast(base_price as decimal(10,2)) as base_price
from {{ ref('raw_products') }}

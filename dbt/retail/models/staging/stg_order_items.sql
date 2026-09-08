{{ config(materialized='view') }}

-- Cast item-level numeric fields while preserving one row per order line.
select
  order_line_id,
  order_id,
  product_id,
  cast(quantity as integer) as quantity,
  cast(unit_price as decimal(10,2)) as unit_price,
  cast(line_amount as decimal(12,2)) as line_amount
from {{ ref('raw_order_items') }}

{{ config(materialized='table') }}

-- Build one row per store with aggregated order performance.
select
  s.store_id,
  s.store_name,
  s.city,
  s.region,
  s.opened_date,
  s.store_type,
  count(distinct o.order_id) as total_orders,
  coalesce(sum(o.order_amount), 0) as total_order_value,
  min(o.order_date) as first_order_date,
  max(o.order_date) as latest_order_date
from {{ ref('stg_stores') }} s
left join {{ ref('stg_orders') }} o
  on s.store_id = o.store_id
group by
  s.store_id,
  s.store_name,
  s.city,
  s.region,
  s.opened_date,
  s.store_type

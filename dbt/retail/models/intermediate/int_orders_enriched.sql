{{ config(materialized='view') }}

-- Enrich each order with customer and store attributes.
select
  o.order_id,
  o.customer_id,
  o.store_id,
  c.customer_name,
  c.email,
  c.city as customer_city,
  c.signup_date,
  s.store_name,
  s.city as store_city,
  s.region as store_region,
  s.store_type,
  o.order_date,
  o.order_amount,
  o.order_status
from {{ ref('stg_orders') }} o
left join {{ ref('stg_customers') }} c
  on o.customer_id = c.customer_id
left join {{ ref('stg_stores') }} s
  on o.store_id = s.store_id

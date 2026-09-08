{{ config(materialized='table') }}

-- Build one row per customer with order history metrics.
select
  c.customer_id,
  c.customer_name,
  c.email,
  c.city,
  c.signup_date,
  min(o.order_date) as first_order_date,
  max(o.order_date) as latest_order_date,
  count(distinct o.order_id) as total_orders,
  coalesce(sum(o.order_amount), 0) as lifetime_order_value
from {{ ref('stg_customers') }} c
left join {{ ref('stg_orders') }} o
  on c.customer_id = o.customer_id
group by
  c.customer_id,
  c.customer_name,
  c.email,
  c.city,
  c.signup_date

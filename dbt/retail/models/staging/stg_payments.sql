{{ config(materialized='view') }}

-- Normalize payment attributes before building payment rollups.
select
  payment_id,
  order_id,
  payment_date,
  cast(payment_amount as decimal(12,2)) as payment_amount,
  lower(payment_method) as payment_method,
  lower(payment_status) as payment_status
from {{ ref('raw_payments') }}

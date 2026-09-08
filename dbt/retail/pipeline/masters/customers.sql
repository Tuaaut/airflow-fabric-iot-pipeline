{{ config(materialized='table') }}

-- Generate a reusable customer master for the retail demo.
with base as (
  select i as customer_id
  from range(1, 121) as t(i)
)

select
  customer_id,
  'customer_' || lpad(cast(customer_id as varchar), 3, '0') as customer_name,
  'customer_' || lpad(cast(customer_id as varchar), 3, '0') || '@example.com' as email,
  date '2023-01-01' + cast(((customer_id * 7) % 365) as integer) as signup_date,
  case customer_id % 6
    when 0 then 'bangkok'
    when 1 then 'chiang mai'
    when 2 then 'phuket'
    when 3 then 'khon kaen'
    when 4 then 'chonburi'
    else 'hat yai'
  end as city
from base

{{ config(materialized='view') }}

-- Standardize customer text fields while keeping the customer grain unchanged.
select
  customer_id,
  upper(customer_name) as customer_name,
  lower(email) as email,
  signup_date,
  city
from {{ ref('raw_customers') }}

{{ config(materialized='view') }}
select * from {{ source('retail_landing', 'payments') }}


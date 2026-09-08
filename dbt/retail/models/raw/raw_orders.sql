{{ config(materialized='view') }}
select * from {{ source('retail_landing', 'orders') }}


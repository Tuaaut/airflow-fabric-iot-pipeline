{{ config(materialized='table') }}

-- Generate store master data that orders can reference.
with base as (
  select i as store_id
  from range(101, 113) as t(i)
)

select
  store_id,
  case store_id
    when 101 then 'bangkok central'
    when 102 then 'bangkok north'
    when 103 then 'chiang mai plaza'
    when 104 then 'phuket beach'
    when 105 then 'khon kaen mall'
    when 106 then 'chonburi port'
    when 107 then 'hat yai point'
    when 108 then 'bangkok east'
    when 109 then 'udon center'
    when 110 then 'korat square'
    when 111 then 'rayong town'
    else 'surat hub'
  end as store_name,
  case store_id
    when 101 then 'bangkok'
    when 102 then 'bangkok'
    when 103 then 'chiang mai'
    when 104 then 'phuket'
    when 105 then 'khon kaen'
    when 106 then 'chonburi'
    when 107 then 'hat yai'
    when 108 then 'bangkok'
    when 109 then 'udon thani'
    when 110 then 'nakhon ratchasima'
    when 111 then 'rayong'
    else 'surat thani'
  end as city,
  case
    when store_id in (101, 102, 108) then 'central'
    when store_id in (103) then 'north'
    when store_id in (104, 107, 112) then 'south'
    when store_id in (105, 109, 110) then 'northeast'
    else 'east'
  end as region,
  date '2022-01-01' + cast(((store_id - 101) * 20) as integer) as opened_date,
  case
    when store_id in (101, 103) then 'flagship'
    when store_id in (102, 108) then 'express'
    else 'branch'
  end as store_type
from base

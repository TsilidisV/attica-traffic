select
    -- identifiers
    device_id,

    -- timestamps
    processed_at,
    processed_year,
    processed_month,
    dayname(processed_at) as "processed_day",
    hour(processed_at) as "processed_hour",
    ingested_at,
        
    -- traffic info
    counted_cars,
    average_speed,

from {{ ref("stg_traffic") }}
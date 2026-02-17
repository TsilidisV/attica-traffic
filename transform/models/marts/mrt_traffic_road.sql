select
    -- identifiers
    m.device_id,

    -- timestamps
    m.processed_at,
    m.processed_date,
    m.processed_year,
    m.processed_month,
    m.processed_day,
    m.processed_hour,
    m.ingested_at,
        
    -- traffic info
    m.counted_cars,
    m.average_speed,

    -- road info
    r.road_name

from {{ ref("fct_measurements") }} as m
LEFT JOIN {{ ref("dim_roads") }} as r
    ON m.device_id = r.device_id
WHERE m.is_quality = true
ORDER BY m.processed_at, r.road_name

{{
    config(
        unique_key=['device_id', 'processed_at'],
        incremental_strategy='merge'
    )
}}

WITH filtered_source AS (
    -- 1. Filter source to only new data
    SELECT * FROM {{ ref("stg_traffic") }}
    {% if is_incremental() %}
        WHERE ingested_at > (SELECT MAX(ingested_at) FROM {{ this }})
    {% endif %}
),

range_bounds AS (
    -- 2. Determine the start and end date for each device IN THIS BATCH
    -- Note: This calculates the range based only on the filtered data.
    SELECT 
        device_id,
        MIN(processed_at) as start_date,
        MAX(processed_at) as end_date
    FROM filtered_source
    GROUP BY device_id
),

complete_calendar AS (
    -- 3. Generate the full sequence of dates for each device
    SELECT 
        device_id,
        -- unnest expands the array of dates into rows
        unnest(generate_series(start_date, end_date, INTERVAL 1 HOUR)) as hourly_slot
    FROM range_bounds
)

-- 4. Join back to the FILTERED source
SELECT 
    -- identifiers
    cal.device_id,

    -- timestamps
    cal.hourly_slot as processed_at,
    cast(cal.hourly_slot as DATE) as processed_date,
    year(cal.hourly_slot) as processed_year,
    month(cal.hourly_slot) as processed_month,
    dayname(cal.hourly_slot) as "processed_day",
    strftime(cal.hourly_slot, '%H:%M')  as "processed_hour",
    origin.ingested_at,
        
    -- traffic info
    origin.counted_cars,
    origin.average_speed,

    -- Ghost readings
    case 
        when origin.counted_cars = 0 and origin.average_speed > 0 then true
        when origin.counted_cars > 0 and origin.average_speed = 0 then true
        else false
    end as is_ghost_reading,

    -- Dead sensors
    case 
        when origin.counted_cars = 0 and origin.average_speed = 0 then true
        else false
    end as is_dead,

    -- Physical impossibilities
    case 
        when origin.average_speed > 130 then true 
        else false 
    end as is_impossible_speed,

    -- Data quality
    case
        when is_ghost_reading
          or is_dead
          or is_impossible_speed
          or (origin.counted_cars IS NULL)
          then false
        else true
    end as is_quality
FROM complete_calendar cal
LEFT JOIN filtered_source origin 
    ON cal.device_id = origin.device_id 
    AND cal.hourly_slot = origin.processed_at
ORDER BY 
    cal.device_id,
    cal.hourly_slot
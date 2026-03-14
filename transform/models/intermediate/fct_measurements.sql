{{
    config(
        unique_key=['device_id', 'processed_at'],
        incremental_strategy='merge'
    )
}}

WITH device_hours AS (
    -- 1. Create the perfect grid of ALL devices and ALL hours
    SELECT 
        d.device_id,
        h.hourly_slot as processed_at
    FROM {{ ref('dim_roads') }} d
    CROSS JOIN {{ ref('util_hours') }} h
    
    {% if is_incremental() %}
        -- Only generate grid rows for hours we haven't processed yet
        -- COALESCE exists in case the table is empty (dropped or something)
        -- Look 2 days back in case data arrive early
        WHERE h.hourly_slot > (
            SELECT CAST(COALESCE(MAX(processed_at), '1970-01-01 00:00:00'::TIMESTAMP) - INTERVAL 2 DAY AS TIMESTAMP)
            FROM {{ this }}
        )
    {% endif %}
),

source_data AS (
    -- 2. Pull in the raw traffic data
    SELECT * FROM {{ ref("stg_traffic") }}
    
    {% if is_incremental() %}
        -- Only generate grid rows for hours we haven't processed yet
        -- COALESCE exists in case the table is empty (dropped or something)
        -- Look 2 days back in case data arrive early
        WHERE processed_at >= (
            SELECT CAST(COALESCE(MAX(processed_at), '1970-01-01 00:00:00'::TIMESTAMP) - INTERVAL 2 DAY AS TIMESTAMP)
            FROM {{ this }}
        )
    {% endif %}
),

joined_data AS (
    -- 3. Left join the source data onto our perfect grid
    SELECT 
        -- identifiers
        dh.device_id,

        -- timestamps
        dh.processed_at,
        cast(dh.processed_at as DATE) as processed_date,
        year(dh.processed_at) as processed_year,
        month(dh.processed_at) as processed_month,
        dayname(dh.processed_at) as "processed_day",
        strftime(dh.processed_at, '%H:%M') as "processed_hour",
        s.ingested_at,
            
        -- traffic info
        s.counted_cars,
        s.average_speed,

        -- Flags
        CASE 
            WHEN s.counted_cars = 0 AND s.average_speed > 0 THEN true
            WHEN s.counted_cars > 0 AND s.average_speed = 0 THEN true
            ELSE false
        END AS is_ghost_reading,

        CASE 
            WHEN s.counted_cars = 0 AND s.average_speed = 0 THEN true
            ELSE false
        END AS is_dead,

        CASE 
            WHEN s.average_speed > 130 THEN true 
            ELSE false 
        END AS is_impossible_speed,

        CASE 
            WHEN s.ingested_at IS NULL THEN true
            ELSE false
        END AS is_missing,

    FROM device_hours dh
    LEFT JOIN source_data s 
        ON dh.device_id = s.device_id 
        AND dh.processed_at = s.processed_at
)

-- 4. Final selection with strict ANSI compliance for the data quality flag
SELECT 
    *,
    CASE
        WHEN is_ghost_reading
          OR is_missing
          OR is_dead
          OR is_impossible_speed
          OR (counted_cars IS NULL)
          THEN false
        ELSE true
    END AS is_quality
FROM joined_data
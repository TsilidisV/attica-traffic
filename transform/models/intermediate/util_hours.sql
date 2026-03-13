{{ config(materialized='ephemeral') }}

SELECT 
    -- unnest expands the array directly into rows
    unnest(generate_series(
        TIMESTAMP '2020-11-13 00:00:00', -- This is the earliest data date
        -- Cast strips the timezone
        CAST(date_trunc('hour', current_timestamp) AS TIMESTAMP),
        INTERVAL 1 HOUR
    )) AS hourly_slot
WITH bad_data as (
    SELECT *
    FROM {{ ref("fct_measurements") }}
)
SELECT
    processed_year, processed_month, 
    count(*) as readings,
    count(CASE WHEN is_dead = true THEN 1 END) as dead_count,
    100 * dead_count / readings as dead_percent,
    count(CASE WHEN is_ghost_reading = true THEN 1 END) as ghost_count,
    100 * ghost_count / readings as ghost_percent,
    count(CASE WHEN is_impossible_speed = true THEN 1 END) as impossible_speed_count,
    100 * impossible_speed_count / readings as impossible_speed_percent,
    count(CASE WHEN ingested_at IS NULL THEN 1 END) as missing_reading_count,
    100 * missing_reading_count / readings as missing_reading_percent
FROM bad_data
GROUP BY processed_year, processed_month
ORDER BY processed_year, processed_month
WITH max_date AS (
    -- Calculate the latest date ONCE
    SELECT MAX(processed_date) as latest_date
    FROM {{ ref("mrt_traffic_road") }}
)
SELECT
    SUM(average_speed * counted_cars * 1.0) / NULLIF(SUM(counted_cars), 0) AS weighted_avg_speed,
    SUM(counted_cars) AS sum_counted_cars,
    COUNT(DISTINCT road_name) AS distinct_roads_count,
    COUNT(DISTINCT device_id) AS distinct_devices_count
FROM {{ ref("mrt_traffic_road") }}
CROSS JOIN max_date
WHERE processed_at >= (max_date.latest_date - 60)
  AND processed_at <  (max_date.latest_date - 30)
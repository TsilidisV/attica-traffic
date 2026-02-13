SELECT
    SUM(average_speed * counted_cars * 1.0) / NULLIF(SUM(counted_cars), 0) AS weighted_avg_speed,
    SUM(counted_cars) AS sum_counted_cars,
    COUNT(DISTINCT road_name) AS distinct_roads_count, 
    COUNT(DISTINCT device_id) AS distinct_devices_count, 
   MAX( processed_at ) AS latest_timestamp -- Wrap in MAX() to satisfy syntax
FROM {{ ref("mrt_last_30_days_traffic_road") }}
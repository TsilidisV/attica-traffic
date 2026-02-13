SELECT
    road_name,
    processed_hour,
    processed_day,
    SUM(average_speed * counted_cars * 1.0) / NULLIF(SUM(counted_cars), 0) AS weighted_avg_speed,
    AVG(counted_cars) as avg_counted_cars
FROM {{ ref('mrt_traffic_road') }}
GROUP BY road_name, processed_hour, processed_day
ORDER BY road_name, processed_day, processed_hour
SELECT
    road_name,
    processed_hour,
    AVG(average_speed) as avg_average_speed,
    AVG(counted_cars) as avg_counted_cars
FROM {{ ref('mrt_traffic_road') }}
GROUP BY road_name, processed_hour
ORDER BY road_name, processed_hour
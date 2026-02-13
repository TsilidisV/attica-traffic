SELECT
    road_name,
    SUM(average_speed * counted_cars * 1.0) / NULLIF(SUM(counted_cars), 0) AS weighted_avg_speed,
    stddev(average_speed) as std_average_speed
FROM {{ ref('mrt_traffic_road') }}
GROUP BY road_name
ORDER BY std_average_speed DESC
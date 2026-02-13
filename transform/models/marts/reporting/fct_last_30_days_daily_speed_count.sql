SELECT processed_date, SUM(counted_cars) as total_counted_cars, SUM(average_speed * counted_cars * 1.0) / NULLIF(SUM(counted_cars), 0) AS weighted_avg_speed,
FROM {{ ref('mrt_last_30_days_traffic_road') }}
GROUP BY processed_date
ORDER BY processed_date
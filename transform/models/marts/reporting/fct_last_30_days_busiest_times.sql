WITH traffic_data AS (
    SELECT 
        processed_day, 
        processed_hour, 
        SUM(average_speed * counted_cars * 1.0) / NULLIF(SUM(counted_cars), 0) AS weighted_avg_speed
    FROM {{ ref('mrt_last_30_days_traffic_road') }}
    GROUP BY 1, 2 
),
min_max_calc AS (
    SELECT 
        *,
        MIN(weighted_avg_speed) OVER() as global_min,
        MAX(weighted_avg_speed) OVER() as global_max
    FROM traffic_data
)
SELECT 
    processed_day, 
    processed_hour, 
    weighted_avg_speed
FROM min_max_calc
WHERE weighted_avg_speed = global_min 
   OR weighted_avg_speed = global_max
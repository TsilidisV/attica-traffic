WITH max_date AS (
    SELECT MAX(processed_date) as latest_date
    FROM {{ ref("mrt_traffic_road") }}
)
SELECT traffic.*
FROM {{ ref("mrt_traffic_road") }} traffic
CROSS JOIN max_date
WHERE traffic.processed_date >= (max_date.latest_date - 30)
ORDER BY traffic.processed_at, traffic.road_name
with source as (
    select * from {{ source('huggingface', 'raw_traffic') }}
),

renamed_and_typed as (
    select
        -- identifiers
        cast(deviceid as VARCHAR) as device_id,

        -- timestamps
        cast(appprocesstime as TIMESTAMP) as processed_at,
        cast(year as SMALLINT) as year,
        cast(month as SMALLINT) as month,
        ingested_at,
        
        -- traffic info
        cast(countedcars as BIGINT) as counted_cars,
        cast(average_speed as DOUBLE) as average_speed,
        
        -- road info
        road_name,
        road_info

    from source
)

select * from renamed_and_typed

-- Sample records for dev environment using deterministic date filter
{% if target.name == 'dev' %}
where processed_at >= '2026-01-01'
{% endif %}
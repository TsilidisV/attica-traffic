{{
    config(
        unique_key='traffic_id',
        incremental_strategy='merge' 
    )
}}

with source as (
    select * from {{ source('huggingface', 'raw_traffic') }}
    
    -- 1. Incremental Filter: Only get new rows since the last run
    {% if is_incremental() %}
        where ingested_at > (select max(ingested_at) from {{ this }})
    {% endif %}
),

renamed_and_typed as (
    select       
        -- primary key
        deviceid || '-' || cast(appprocesstime as VARCHAR) as traffic_id,

        -- identifiers
        cast(deviceid as VARCHAR) as device_id,

        -- timestamps
        cast(appprocesstime as TIMESTAMP) as processed_at,
        cast(appprocesstime as DATE) as processed_date,
        cast(year as SMALLINT) as processed_year,
        cast(month as SMALLINT) as processed_month,
        ingested_at,
        
        -- traffic info
        cast(countedcars as BIGINT) as counted_cars,
        cast(average_speed as DOUBLE) as average_speed,
        
        -- road info
        road_name,
        road_info

    from source
),

deduplicated as (
    select * from renamed_and_typed
    
    -- 2. Deduplicate logic (unchanged, but handles the smaller batch)
    -- This ensures that if the source sends duplicates for the same second, 
    -- we only insert the first one.
    qualify row_number() over(
        partition by device_id, processed_at
        order by processed_at
    ) = 1
)

select * from deduplicated
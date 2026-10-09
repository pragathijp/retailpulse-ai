with source as (
    select * from {{ source('raw', 'retail_transactions') }}
),

renamed as (
    select
        trim(invoice_no) as invoice_no,
        trim(stock_code) as stock_code,
        trim(description) as description,
        cast(quantity as integer) as quantity,
        cast(invoice_ts as timestamp) as invoice_ts,
        cast(unit_price as decimal(18, 4)) as unit_price,
        nullif(trim(customer_id), '') as customer_id,
        trim(country) as country,
        source_variant,
        case 
            when invoice_no like 'C%' or quantity < 0 then true 
            else false 
        end as is_cancellation,
        cast(quantity * unit_price as decimal(18, 4)) as gross_revenue
    from source
)

select * from renamed

-- raw rows = staged rows + exact duplicates removed + invalid rows dropped
select 'mismatch' as failure
from (
    select
        max(case when check_name = 'raw_rows' then check_value end) as raw_rows,
        max(case when check_name = 'staged_rows' then check_value end) as staged_rows,
        max(case when check_name = 'exact_duplicates_removed' then check_value end) as dup_removed,
        max(case when check_name = 'invalid_rows_dropped' then check_value end) as invalid_dropped
    from {{ ref('audit_data_quality') }}
)
where raw_rows <> staged_rows + dup_removed + invalid_dropped

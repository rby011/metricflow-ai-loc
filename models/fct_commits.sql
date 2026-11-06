-- Grain: one row per (repository, commit SHA). Latest ingestion wins.
with ranked as (
    select *, row_number() over (
        partition by repository, commit_sha
        order by cast(ingested_at as timestamptz) desc, event_id desc
    ) as ingestion_rank
    from {{ ref('raw_commits') }}
)
select
    repository || ':' || commit_sha as commit_key,
    commit_sha,
    repository,
    organization,
    agent,
    author_id,
    cast(cast(committed_at as timestamptz) at time zone 'Asia/Seoul' as date) as committed_date,
    cast(committed_at as timestamptz) as committed_at,
    cast(added_loc as bigint) as added_loc,
    cast(deleted_loc as bigint) as deleted_loc,
    cast(ai_added_loc as bigint) as ai_added_loc
from ranked
where ingestion_rank = 1
  and not cast(is_merge as boolean)
  and not cast(is_bot as boolean)

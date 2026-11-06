select * from {{ ref('fct_commits') }}
where added_loc < 0 or deleted_loc < 0 or ai_added_loc < 0
   or ai_added_loc > added_loc
   or added_loc is null or deleted_loc is null or ai_added_loc is null

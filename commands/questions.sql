SELECT
    id,
    tags,
    body,
    score,
    title,
    view_count,
    answer_count,
    owner_user_id,
    comment_count,
    creation_date,
    accepted_answer_id
FROM
    `bigquery-public-data.stackoverflow.posts_questions`
WHERE
    creation_date >= TIMESTAMP(@start_date)
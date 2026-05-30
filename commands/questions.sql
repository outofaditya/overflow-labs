SELECT
    Id,
    Score,
    Title,
    Tags,
    Body,
    ViewCount,
    OwnerUserId,
    AnswerCount,
    ClosedDate,
    CommentCount,
    CreationDate,
    LastActivityDate,
    AcceptedAnswerId
FROM
    posts
WHERE
    PostTypeId = 1
    AND CreationDate >= $start_date
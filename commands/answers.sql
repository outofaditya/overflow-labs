SELECT
    Id,
    Score,
    Body,
    ParentId,
    OwnerUserId,
    CommentCount,
    CreationDate
FROM posts
WHERE PostTypeId = 2
  AND CreationDate >= $start_date
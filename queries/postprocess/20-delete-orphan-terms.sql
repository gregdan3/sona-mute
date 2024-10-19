/* Most of disk space savings are here */
DELETE FROM term
WHERE
  id NOT IN (
    SELECT DISTINCT
      term_id
    FROM
      monthly
  );

/* Most of disk space savings are here */
DELETE FROM phrase
WHERE
  id NOT IN (
    SELECT DISTINCT
      phrase_id
    FROM
      monthly
  );

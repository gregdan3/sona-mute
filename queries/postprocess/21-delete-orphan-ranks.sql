DELETE FROM ranks
WHERE
  phrase_id NOT IN (
    SELECT
      id
    FROM
      phrase
  );

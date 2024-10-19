DELETE FROM yearly
WHERE
  phrase_id NOT IN (
    SELECT
      id
    FROM
      phrase
  );

DELETE FROM yearly
WHERE
  term_id NOT IN (
    SELECT
      id
    FROM
      term
  );

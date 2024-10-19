-- if db is well formed, the totals table will have the same number of hits as
-- the sum of the monthly table
-- however, this assumption will need to be revisited if i correct it in edgedb in the
-- future
SELECT
  t.text AS term,
  sum(mo.hits)
FROM
  monthly mo
  JOIN term t ON mo.term_id = t.id
WHERE
  t.len = 1
  AND mo.min_sent_len = 1
  -- AND day >= 1690848000
  -- AND day < 1722470400
GROUP BY
  t.text
EXCEPT
SELECT
  t.text AS term,
  yr.hits
FROM
  yearly yr
  JOIN term t ON yr.term_id = t.id
WHERE
  t.len = 1
  AND yr.min_sent_len = 1
  AND yr.day = 0;

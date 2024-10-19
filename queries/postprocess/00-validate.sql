-- if db is well formed, the totals table will have the same number of hits as
-- the sum of the monthly table
-- however, this assumption will need to be revisited if i correct it in edgedb in the
-- future
SELECT
  p.text AS term,
  sum(mo.hits)
FROM
  monthly mo
  JOIN phrase p ON mo.phrase_id = p.id
WHERE
  p.len = 1
  AND mo.min_sent_len = 1
  -- AND day >= 1690848000
  -- AND day < 1722470400
GROUP BY
  p.text
EXCEPT
SELECT
  p.text AS term,
  yr.hits
FROM
  yearly yr
  JOIN phrase p ON yr.phrase_id = p.id
WHERE
  p.len = 1
  AND yr.min_sent_len = 1
  AND yr.day = 0;

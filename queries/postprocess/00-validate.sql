-- if db is well formed, the totals table will have the same number of occurrences as
-- the sum of the frequency table
-- however, this assumption will need to be revisited if i correct it in edgedb in the
-- future
SELECT
  p.text AS term,
  sum(r.occurrences)
FROM
  frequency r
  JOIN phrase p ON r.phrase_id = p.id
WHERE
  p.len = 1
  AND r.min_sent_len = 1
  -- AND day >= 1690848000
  -- AND day < 1722470400
GROUP BY
  p.text
EXCEPT
SELECT
  p.text AS term,
  r.occurrences
FROM
  ranks r
  JOIN phrase p ON r.phrase_id = p.id
WHERE
  p.len = 1
  AND r.min_sent_len = 1
  AND r.day = 0;

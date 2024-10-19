/* Remove terms below a certain number of hits, here 40
* Partly for anonymity, but mostly for Google's reasons: the data is massive if you don't do this */
WITH
  summed_hits AS (
    SELECT
      mo.term_id,
      SUM(mo.hits) AS total_hits
    FROM
      monthly mo
      JOIN term t ON mo.term_id = t.id
    WHERE
      /* yes this is nonsense */
      (
        mo.min_sent_len = 1
        AND len = 1
      )
      OR (
        mo.min_sent_len = 2
        AND len = 2
      )
      OR (
        mo.min_sent_len = 3
        AND len = 3
      )
      OR (
        mo.min_sent_len = 4
        AND len = 4
      )
      OR (
        mo.min_sent_len = 5
        AND len = 5
      )
      OR (
        mo.min_sent_len = 6
        AND len = 6
      )
      OR (
        mo.min_sent_len = 7
        AND len = 7
      )
    GROUP BY
      term_id
  ),
  terms_to_delete AS (
    SELECT
      term_id
    FROM
      summed_hits
    WHERE
      total_hits < 40
  )
DELETE FROM monthly
WHERE
  term_id IN (
    SELECT
      term_id
    FROM
      terms_to_delete
  );

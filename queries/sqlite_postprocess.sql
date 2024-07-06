WITH
  summed_occurrences AS (
    SELECT
      phrase_id,
      min_sent_len,
      SUM(occurrences) AS total_occurrences
    FROM
      frequency
    GROUP BY
      phrase_id,
      min_sent_len
  ),
  phrases_to_delete AS (
    SELECT
      phrase_id
    FROM
      summed_occurrences
    WHERE
      total_occurrences < 40
  )
DELETE FROM frequency
WHERE
  phrase_id IN (
    SELECT
      phrase_id
    FROM
      phrases_to_delete
  );

DELETE FROM phrase
WHERE
  id NOT IN (
    SELECT DISTINCT
      phrase_id
    FROM
      frequency
  );

CREATE INDEX FreqCovering on frequency (phrase_id, min_sent_len, day, occurrences);

pragma journal_mode = delete;

pragma page_size = 1024;

vacuum;

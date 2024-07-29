/* Remove words/phrases below a certain number of occurrences, here 40
* Partly for anonymity, but mostly for Google's reasons: the data is massive if you don't do this */
WITH
  summed_occurrences AS (
    SELECT
      f.phrase_id,
      SUM(f.occurrences) AS total_occurrences
    FROM
      frequency f
      JOIN phrase p ON f.phrase_id = p.id
    WHERE
      /* yes this is nonsense */
      (
        f.min_sent_len = 1
        AND len = 1
      )
      OR (
        f.min_sent_len = 2
        AND len = 2
      )
      OR (
        f.min_sent_len = 3
        AND len = 3
      )
      OR (
        f.min_sent_len = 4
        AND len = 4
      )
      OR (
        f.min_sent_len = 5
        AND len = 5
      )
      OR (
        f.min_sent_len = 6
        AND len = 6
      )
    GROUP BY
      phrase_id
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

/* Most of disk space savings are here */
DELETE FROM phrase
WHERE
  id NOT IN (
    SELECT DISTINCT
      phrase_id
    FROM
      frequency
  );

DELETE FROM ranks
WHERE
  phrase_id NOT IN (
    SELECT
      id
    FROM
      phrase
  );

CREATE INDEX FreqCovering on frequency (phrase_id, min_sent_len, day, occurrences);

CREATE INDEX TotalCovering on total (phrase_len, min_sent_len, day, occurrences);

CREATE INDEX RanksCovering on ranks (phrase_id, min_sent_len, day, occurrences);

/* For HttpVFS performance */
pragma journal_mode = delete;

pragma page_size = 1024;

vacuum;

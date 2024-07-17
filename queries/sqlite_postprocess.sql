/* Remove words/phrases below a certain number of occurrences, here 40
* Partly for anonymity, but mostly for Google's reasons: the data is massive if you don't do this */
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

/* NOTE: Deletes the last month from the data
* This is presumed to be safe due to the data being incomplete
* May not be safe if data was collected on the last day of the month exactly */
DELETE FROM frequency
WHERE
  day IN (
    SELECT
      MAX(day)
    FROM
      frequency
  );

DELETE FROM total
WHERE
  day IN (
    SELECT
      MAX(day)
    FROM
      total
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

CREATE INDEX FreqCovering on frequency (phrase_id, min_sent_len, day, occurrences);

CREATE INDEX TotalCovering on total (phrase_len, min_sent_len, day, occurrences);

/* For HttpVFS performance */
pragma journal_mode = delete;

pragma page_size = 1024;

vacuum;

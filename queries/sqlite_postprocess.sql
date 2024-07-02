/* To maintain the anonymity of the dataset, I remove words with fewer than 100 occurrences across the entire dataset.
* This would be *extremely* difficult to do while generating this data, */
DELETE FROM word_freq
WHERE
  (word, min_length) IN (
    SELECT
      word,
      min_length
    FROM
      (
        SELECT
          word,
          min_length,
          SUM(occurrences) AS total_occurrences
        FROM
          word_freq
        GROUP BY
          word,
          min_length
        HAVING
          SUM(occurrences) < 100
      ) AS t
  );


DELETE FROM phrase_freq
WHERE
  (phrase, length) IN (
    SELECT
      phrase,
      length
    FROM
      (
        SELECT
          phrase,
          length,
          SUM(occurrences) AS n
        FROM
          phrase_freq
        GROUP BY
          phrase,
          length
        HAVING
          SUM(occurrences) < 100
      ) AS t
  );


-- Delete from word_freq where sum of occurrences < 100
DELETE FROM word_freq
WHERE (word_id, min_len) IN (
    SELECT word_id, min_len
    FROM word_freq
    GROUP BY word_id, min_len
    HAVING SUM(occurrences) < 100
);

-- Delete from phrase_freq where sum of occurrences < 100
DELETE FROM phrase_freq
WHERE (word_id, length) IN (
    SELECT word_id, length
    FROM phrase_freq
    GROUP BY word_id, length
    HAVING SUM(occurrences) < 100
);

-- Delete from word where word_id is no longer referenced in word_freq or phrase_freq
DELETE FROM word
WHERE id NOT IN (SELECT word_id FROM word_freq)
AND id NOT IN (SELECT word_id FROM phrase_freq);

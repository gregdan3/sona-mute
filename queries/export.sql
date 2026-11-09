CREATE TEMP TABLE term_export_map AS
SELECT
    id AS old_id,
    row_number() OVER (
      ORDER BY 
        len ASC,
        hits DESC,
        id
    ) AS new_id
FROM (
    SELECT
      t.id,
      t.len,
      SUM(f.hits) AS hits
    FROM term t
    JOIN alltime f ON f.term_id = t.id
    WHERE 
      f.hits >= 25 -- must appear 25 times ever
      AND attr = 'All' -- position doesn't matter
    GROUP BY t.id, t.len
) x;

CREATE UNIQUE INDEX term_export_map_old_id_idx
    ON term_export_map (old_id);

ANALYZE term_export_map;

\copy ( SELECT m.new_id AS id, t.len, array_to_string(t.words, ' ') AS text FROM term t JOIN term_export_map m ON m.old_id = t.id ORDER BY m.new_id) TO 'dumps/terms.csv' WITH (FORMAT CSV, HEADER);

\copy ( SELECT m.new_id AS term_id, array_position(enum_range(NULL::attribute), x.attr) - 1 AS attr, EXTRACT(EPOCH FROM (x.day AT TIME ZONE 'UTC'))::bigint AS day, x.hits, x.authors_nt AS authors FROM monthly x JOIN term_export_map m ON m.old_id = x.term_id) TO 'dumps/monthly.csv' WITH (FORMAT CSV, HEADER);

\copy ( SELECT m.new_id AS term_id, array_position(enum_range(NULL::attribute), x.attr) - 1 AS attr, EXTRACT(EPOCH FROM (x.day AT TIME ZONE 'UTC'))::bigint AS day, x.hits, x.authors_nt AS authors FROM yearly x JOIN term_export_map m ON m.old_id = x.term_id  UNION ALL SELECT m.new_id AS term_id, array_position(enum_range(NULL::attribute), x.attr) - 1 AS attr, 0 AS day, x.hits, x.authors_nt AS authors FROM alltime x JOIN term_export_map m ON m.old_id = x.term_id) TO 'dumps/yearly.csv' WITH (FORMAT CSV, HEADER);

\copy ( SELECT x.len, array_position(enum_range(NULL::attribute), x.attr) - 1 AS attr, EXTRACT(EPOCH FROM (x.day AT TIME ZONE 'UTC'))::bigint AS day, x.hits, x.authors_nt AS authors FROM total_monthly x) TO 'dumps/total_monthly.csv' WITH (FORMAT CSV, HEADER);

\copy ( SELECT x.len, array_position(enum_range(NULL::attribute), x.attr) - 1 AS attr, EXTRACT(EPOCH FROM (x.day AT TIME ZONE 'UTC'))::bigint AS day, x.hits, x.authors_nt AS authors FROM total_yearly x UNION ALL SELECT x.len, array_position(enum_range(NULL::attribute), x.attr) - 1 AS attr, 0 AS day, x.hits, x.authors_nt AS authors FROM total_alltime x) TO 'dumps/total_yearly.csv' WITH (FORMAT CSV, HEADER);

CREATE MATERIALIZED VIEW term_sqlite_map AS
SELECT
    id AS old_id,
    row_number() OVER (
        ORDER BY len ASC, hits DESC, id
    ) AS new_id
FROM (
    SELECT
        t.id,
        t.len,
        sum(f.hits) AS hits
    FROM term t
    JOIN alltime f ON f.term_id = t.id
    WHERE
        f.hits >= 40
        AND f.attr = 'All'
    GROUP BY t.id, t.len
) x;

CREATE VIEW term_sqlite AS
SELECT
    m.new_id AS id,
    t.len,
    array_to_string(t.words, ' ') AS text
FROM term t
JOIN term_sqlite_map m ON m.old_id = t.id;

CREATE VIEW monthly_sqlite AS
SELECT
    m.new_id AS term_id,
    array_position(enum_range(NULL::attribute), x.attr) - 1 AS attr,
    extract(epoch FROM (x.day AT TIME ZONE 'UTC'))::bigint AS day,
    x.hits,
    x.authors_nt AS authors
FROM monthly x
JOIN term_sqlite_map m ON m.old_id = x.term_id;

CREATE VIEW yearly_sqlite AS
SELECT
    m.new_id AS term_id,
    array_position(enum_range(NULL::attribute), x.attr) - 1 AS attr,
    extract(epoch FROM (x.day AT TIME ZONE 'UTC'))::bigint AS day,
    x.hits,
    x.authors_nt AS authors
FROM yearly x
JOIN term_sqlite_map m ON m.old_id = x.term_id

UNION ALL

SELECT
    m.new_id AS term_id,
    array_position(enum_range(NULL::attribute), x.attr) - 1 AS attr,
    0 AS day,
    x.hits,
    x.authors_nt AS authors
FROM alltime x
JOIN term_sqlite_map m ON m.old_id = x.term_id;

CREATE VIEW total_monthly_sqlite AS
SELECT
    x.len AS term_len,
    array_position(enum_range(NULL::attribute), x.attr) - 1 AS attr,
    extract(epoch FROM (x.day AT TIME ZONE 'UTC'))::bigint AS day,
    x.hits,
    x.authors_nt AS authors
FROM total_monthly x;

CREATE VIEW total_yearly_sqlite AS
SELECT
    x.len AS term_len,
    array_position(enum_range(NULL::attribute), x.attr) - 1 AS attr,
    extract(epoch FROM (x.day AT TIME ZONE 'UTC'))::bigint AS day,
    x.hits,
    x.authors_nt AS authors
FROM total_yearly x

UNION ALL

SELECT
    x.len AS term_len,
    array_position(enum_range(NULL::attribute), x.attr) - 1 AS attr,
    0 AS day,
    x.hits,
    x.authors_nt AS authors
FROM total_alltime x;

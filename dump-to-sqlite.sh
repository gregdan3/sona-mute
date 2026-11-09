#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 5 ]]; then
  echo "Usage: $0 <host> <port> <user> <database> <sqlite_target>" >&2
  exit 1
fi

PGHOST="$1"
PGPORT="$2"
PGUSER="$3"
PGDATABASE="$4"
SQLITE_DB="$(realpath -m "$5")"

if [[ -z "${PGPASSWORD:-}" ]]; then
  echo "Error: PGPASSWORD must be set" >&2
  exit 1
fi

if [[ -e "$SQLITE_DB" ]]; then
  echo "Error: Target database already exists: $SQLITE_DB" >&2
  exit 1
fi

mkdir -p "$(dirname "$SQLITE_DB")"
echo "Creating SQLite database: $SQLITE_DB"
export SQLITE_DB

########################
# create sqlite schema #
########################

sqlite3 "$SQLITE_DB" <<'SQL'
.bail on

PRAGMA journal_mode = WAL;

CREATE TABLE term (
    id INTEGER NOT NULL,
    len INTEGER NOT NULL,
    text TEXT NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (text)
) WITHOUT ROWID;

CREATE TABLE monthly (
    term_id INTEGER NOT NULL,
    attr INTEGER NOT NULL,
    day INTEGER NOT NULL,
    hits INTEGER NOT NULL,
    authors INTEGER NOT NULL,
    PRIMARY KEY (term_id, attr, day),
    FOREIGN KEY (term_id) REFERENCES term(id)
) WITHOUT ROWID;

CREATE TABLE yearly (
    term_id INTEGER NOT NULL,
    attr INTEGER NOT NULL,
    day INTEGER NOT NULL,
    hits INTEGER NOT NULL,
    authors INTEGER NOT NULL,
    PRIMARY KEY (term_id, attr, day),
    FOREIGN KEY (term_id) REFERENCES term(id)
) WITHOUT ROWID;

CREATE TABLE total_monthly (
    term_len INTEGER NOT NULL,
    attr INTEGER NOT NULL,
    day INTEGER NOT NULL,
    hits INTEGER NOT NULL,
    authors INTEGER NOT NULL,
    PRIMARY KEY (day, term_len, attr)
) WITHOUT ROWID;

CREATE TABLE total_yearly (
    term_len INTEGER NOT NULL,
    attr INTEGER NOT NULL,
    day INTEGER NOT NULL,
    hits INTEGER NOT NULL,
    authors INTEGER NOT NULL,
    PRIMARY KEY (day, term_len, attr)
) WITHOUT ROWID;
SQL

###########################
# dump postgres to sqlite #
###########################

export SQLITE_DB

psql \
  --no-psqlrc \
  --set ON_ERROR_STOP=1 \
  --host "$PGHOST" \
  --port "$PGPORT" \
  --user "$PGUSER" \
  --dbname "$PGDATABASE" <<'SQL'

-- maps arbitrary term id of source to new term id ordered for table scan. 
-- seems weird, but my deployment (sqlite over http vfs) demands weird things
-- for performance. shouldn't matter if a covering index is used though
CREATE TEMP TABLE term_export_map AS
SELECT
    id AS old_id,
    row_number() OVER (
        ORDER BY len ASC, hits DESC, id
    ) AS new_id
FROM (
    SELECT
        t.id,
        t.len,
        SUM(f.hits) AS hits
    FROM term t
    JOIN alltime f ON f.term_id = t.id
    WHERE
        f.hits >= 40
        AND f.attr = 'All'
    GROUP BY t.id, t.len
) x;
CREATE UNIQUE INDEX term_export_map_old_id_idx ON term_export_map (old_id);
ANALYZE term_export_map;

-- dumping terms view
\copy (SELECT m.new_id AS id, t.len, array_to_string(t.words, ' ') AS text FROM term t JOIN term_export_map m ON m.old_id = t.id ORDER BY m.new_id) TO PROGRAM 'sqlite3 "$SQLITE_DB" ".bail on" ".mode csv" "PRAGMA foreign_keys=ON;" ".import --skip 1 /dev/stdin term"' WITH (FORMAT CSV, HEADER);

-- monthly data
\copy (SELECT m.new_id AS term_id, array_position(enum_range(NULL::attribute), x.attr) - 1 AS attr, EXTRACT(EPOCH FROM (x.day AT TIME ZONE 'UTC'))::bigint AS day, x.hits, x.authors_nt AS authors FROM monthly x JOIN term_export_map m ON m.old_id = x.term_id) TO PROGRAM 'sqlite3 "$SQLITE_DB" ".bail on" ".mode csv" "PRAGMA foreign_keys=ON;" ".import --skip 1 /dev/stdin monthly"' WITH (FORMAT CSV, HEADER);

-- yearly and alltime special rows
\copy (SELECT m.new_id AS term_id, array_position(enum_range(NULL::attribute), x.attr) - 1 AS attr, EXTRACT(EPOCH FROM (x.day AT TIME ZONE 'UTC'))::bigint AS day, x.hits, x.authors_nt AS authors FROM yearly x JOIN term_export_map m ON m.old_id = x.term_id UNION ALL SELECT m.new_id AS term_id, array_position(enum_range(NULL::attribute), x.attr) - 1 AS attr, 0 AS day, x.hits, x.authors_nt AS authors FROM alltime x JOIN term_export_map m ON m.old_id = x.term_id) TO PROGRAM 'sqlite3 "$SQLITE_DB" ".bail on" ".mode csv" "PRAGMA foreign_keys=ON;" ".import --skip 1 /dev/stdin yearly"' WITH (FORMAT CSV, HEADER);

-- monthly totals
\copy (SELECT x.len AS term_len, array_position(enum_range(NULL::attribute), x.attr) - 1 AS attr, EXTRACT(EPOCH FROM (x.day AT TIME ZONE 'UTC'))::bigint AS day, x.hits, x.authors_nt AS authors FROM total_monthly x) TO PROGRAM 'sqlite3 "$SQLITE_DB" ".bail on" ".mode csv" ".import --skip 1 /dev/stdin total_monthly"' WITH (FORMAT CSV, HEADER);

-- yearly totals and alltime totals special rows
\copy (SELECT x.len AS term_len, array_position(enum_range(NULL::attribute), x.attr) - 1 AS attr, EXTRACT(EPOCH FROM (x.day AT TIME ZONE 'UTC'))::bigint AS day, x.hits, x.authors_nt AS authors FROM total_yearly x UNION ALL SELECT x.len AS term_len, array_position(enum_range(NULL::attribute), x.attr) - 1 AS attr, 0 AS day, x.hits, x.authors_nt AS authors FROM total_alltime x) TO PROGRAM 'sqlite3 "$SQLITE_DB" ".bail on" ".mode csv" ".import --skip 1 /dev/stdin total_yearly"' WITH (FORMAT CSV, HEADER);

SQL

#################
# index dump db #
#################

sqlite3 "$SQLITE_DB" <<'SQL'
.bail on

CREATE INDEX MonthlyCovering ON monthly (term_id, attr, day, hits, authors);
CREATE INDEX YearlyCovering ON yearly (term_id, attr, day, hits, authors);
CREATE INDEX MonthlyTotalCovering ON total_monthly (term_len, attr, day, hits, authors);
CREATE INDEX YearlyTotalCovering ON total_yearly (term_len, attr, day, hits, authors);
CREATE INDEX YearlyByHits ON yearly (attr ASC, hits DESC, term_id) WHERE day = 0;

pragma journal_mode = delete;
PRAGMA page_size = 1024;
PRAGMA optimize;

VACUUM;
ANALYZE;
ANALYZE;
SQL

sqlite3 -header -column "$SQLITE_DB" <<'SQL'
SELECT 'term' AS table_name, COUNT(1) AS rows FROM term
UNION ALL SELECT 'monthly', COUNT(1) FROM monthly
UNION ALL SELECT 'yearly', COUNT(1) FROM yearly
UNION ALL SELECT 'total_monthly', COUNT(1) FROM total_monthly
UNION ALL SELECT 'total_yearly', COUNT(1) FROM total_yearly;
SQL

echo
echo "Database created: $SQLITE_DB"

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

-- 
\copy (SELECT * FROM term_sqlite ORDER BY id) TO PROGRAM 'sqlite3 "$SQLITE_DB" ".bail on" ".mode csv" "PRAGMA foreign_keys=ON;" ".import --skip 1 /dev/stdin term"' WITH (FORMAT CSV, HEADER);
\copy (SELECT * FROM monthly_sqlite) TO PROGRAM 'sqlite3 "$SQLITE_DB" ".bail on" ".mode csv" "PRAGMA foreign_keys=ON;" ".import --skip 1 /dev/stdin monthly"' WITH (FORMAT CSV, HEADER);
\copy (SELECT * FROM yearly_sqlite) TO PROGRAM 'sqlite3 "$SQLITE_DB" ".bail on" ".mode csv" "PRAGMA foreign_keys=ON;" ".import --skip 1 /dev/stdin yearly"' WITH (FORMAT CSV, HEADER);
\copy (SELECT * FROM total_monthly_sqlite) TO PROGRAM 'sqlite3 "$SQLITE_DB" ".bail on" ".mode csv" ".import --skip 1 /dev/stdin total_monthly"' WITH (FORMAT CSV, HEADER);
\copy (SELECT * FROM total_yearly_sqlite) TO PROGRAM 'sqlite3 "$SQLITE_DB" ".bail on" ".mode csv" ".import --skip 1 /dev/stdin total_yearly"' WITH (FORMAT CSV, HEADER);

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

.bail on
.mode csv

CREATE TABLE term (
        id INTEGER NOT NULL,
        len INTEGER NOT NULL,
        text TEXT NOT NULL,
        PRIMARY KEY (id),
        UNIQUE (text)
    );
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

.import --skip 1 dumps/terms.csv term
.import --skip 1 dumps/monthly.csv monthly
.import --skip 1 dumps/yearly.csv yearly
.import --skip 1 dumps/total_monthly.csv total_monthly
.import --skip 1 dumps/total_yearly.csv total_yearly

CREATE INDEX MonthlyCovering on monthly (term_id, attr, day, hits, authors);
CREATE INDEX YearlyCovering on yearly (term_id, attr, day, hits, authors);
CREATE INDEX MonthlyTotalCovering on total_monthly (term_len, attr, day, hits, authors);
CREATE INDEX YearlyTotalCovering on total_yearly (term_len, attr, day, hits, authors);
CREATE INDEX WildcardIndex ON term (len, text);

PRAGMA optimize;

VACUUM;
ANALYZE;
ANALYZE;

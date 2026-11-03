CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TYPE attribute AS ENUM (
    'All',

    -- positions
    'Start',        -- starts from idx 0
    'End',          -- ends on idx -1
    'Full',         -- starts on idx 0 and ends on idx -1
    'Long',         -- in sentence with >= 4 words
    'Short',        -- in sentence with < 4 words
    'Inner',        -- does not start on idx 0 or end on idx -1

    -- parts of speech
    'Subject',      -- before li
    'Verb',         -- after li and before e
    'Object',       -- after e and before prep
    'PrepositionalObject', -- after prep
    'Predicate'     -- anything after li
    'Interjection', -- non-sentence use; probably duplicate with 'full'?

    -- more specific parts of speech
    'TransitiveVerb',   -- after li, with e
    'IntransitiveVerb', -- after li, without e
    'PrepositionalVerb' -- after li, is first prep+prep object

    -- functions
    'Content',
    'Particle',     -- duplicate with exclusive particles, but not nanpa/preps
    'Head',         -- first word in any part of speech
    'Modifier',     -- following any head in the same part of speech
    'Preposition',  -- prep itself: tawa lon tan sama kepeken
    'Preverb',      -- preverb itself: kama awen lukin alasa ken wile sona
    'Noun',         -- subject or object or prep object

    -- other
    'Unknown'       -- part or function cannot be determined
);


CREATE TABLE platform (
    id smallint PRIMARY KEY,
    name text NOT NULL
);


CREATE TABLE community (
    id uuid NOT NULL,
    platform_id smallint NOT NULL REFERENCES platform (id),
    name text NOT NULL,

    num_sentences int NOT NULL DEFAULT 0,
    num_tp_sentences int NOT NULL DEFAULT 0,

    PRIMARY KEY (id, platform_id)
);


CREATE TABLE author (
    id uuid NOT NULL,
    platform_id smallint NOT NULL REFERENCES platform (id),
    name text NOT NULL,

    is_bot boolean NOT NULL,
    is_webhook boolean NOT NULL,

    num_sentences int NOT NULL DEFAULT 0,
    num_tp_sentences int NOT NULL DEFAULT 0,

    PRIMARY KEY (id, platform_id)
);


CREATE TABLE message (
    id uuid NOT NULL,
    platform_id smallint NOT NULL REFERENCES platform (id),

    author_id uuid NOT NULL,
    community_id uuid NOT NULL,
    container_id int NOT NULL, -- for levels of organization beyond community

    postdate timestamptz NOT NULL,
    content text NOT NULL,
    score real NOT NULL,
    is_counted boolean NOT NULL,

    PRIMARY KEY (id, platform_id),
    CONSTRAINT message_id_community_unique UNIQUE (id, platform_id, community_id),

    FOREIGN KEY (author_id, platform_id) REFERENCES author (id, platform_id) ON DELETE CASCADE,
    FOREIGN KEY (community_id, platform_id) REFERENCES community (id, platform_id) ON DELETE CASCADE
);
CREATE INDEX message_is_counted_postdate_idx
ON message (postdate)
WHERE is_counted = true;


CREATE TABLE sentence (
    -- tracks a unique sequence of words as spoken by a user
    id int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    words text[] NOT NULL UNIQUE,
    len smallint GENERATED ALWAYS AS (cardinality(words)) STORED
);
CREATE INDEX sentence_len_idx ON sentence (len);


CREATE TABLE message_sentence (
    message_id uuid NOT NULL,
    platform_id smallint NOT NULL,
    sentence_id int NOT NULL REFERENCES sentence (id) ON DELETE CASCADE,
    idx smallint NOT NULL, -- order of sentences in message
    score real NOT NULL,

    PRIMARY KEY (message_id, platform_id, idx),
    FOREIGN KEY (message_id, platform_id) REFERENCES message (id, platform_id) ON DELETE CASCADE
);
CREATE INDEX message_sentence_score_idx ON message_sentence (score);

/* NOTE:
 * everything beyond here is calculated from the above.
 * messages and sentences have been scored,
 * and sentences which are both is_counted and have a sufficient score
 * (i.e. which are able to appear in the tp_user_sentence m-view)
 * will be re-examined to find all their Terms */


CREATE TABLE term (
    -- tracks a unique sequence of words as an ngram
    id int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    words text[] NOT NULL UNIQUE,
    len smallint GENERATED ALWAYS AS (cardinality(words)) STORED
    -- hits int NOT NULL DEFAULT 0
  -- NOTE: all counted+sufficiently scored times the term was used; computed after ingest
  -- hits per term can be calculated from
  -- SELECT f.term_id, SUM(fhits) FROM frequency f JOIN context c WHERE c.attr = 0 GROUP BY f.term_id
);
-- CREATE INDEX term_hits_len_idx ON term (hits, len) INCLUDE (text); -- text fetchable from index

CREATE TABLE term_author (
    -- unrolled from `term` to make unique authors countable
    term_id int NOT NULL REFERENCES term (id) ON DELETE CASCADE,
    author_id uuid NOT NULL,
    platform_id smallint NOT NULL,
    hits int NOT NULL DEFAULT 0,
    -- NOTE: same as hits in term but only for this author using this term
    -- hits per author is not calculable from frequency+context; must be inserted

    PRIMARY KEY (term_id, author_id, platform_id),
    FOREIGN KEY (author_id, platform_id) REFERENCES author (id, platform_id) ON DELETE CASCADE
);

CREATE TABLE context (
    id int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    community_id uuid NOT NULL,
    platform_id smallint NOT NULL,
    day date NOT NULL,
    attr attribute NOT NULL,

    CONSTRAINT context_unique UNIQUE (community_id, platform_id, day, attr),
    FOREIGN KEY (community_id, platform_id) REFERENCES community (id, platform_id) ON DELETE CASCADE
);

CREATE TABLE frequency (
    id int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    context_id int NOT NULL REFERENCES context (id) ON DELETE CASCADE,
    term_id int NOT NULL REFERENCES term (id) ON DELETE CASCADE,
    hits int NOT NULL,

    CONSTRAINT context_term_unique UNIQUE (context_id, term_id)
);
CREATE INDEX frequency_term_idx ON frequency (term_id);

CREATE TABLE frequency_author (
    frequency_id int NOT NULL REFERENCES frequency (id) ON DELETE CASCADE,
    author_id uuid NOT NULL,
    platform_id smallint NOT NULL,
    hits int NOT NULL,
    -- NOTE: same as hits in term/term_author but now just in this context

    PRIMARY KEY (frequency_id, author_id, platform_id),
    FOREIGN KEY (author_id, platform_id) REFERENCES author (id, platform_id) ON DELETE CASCADE
);

CREATE MATERIALIZED VIEW tp_user_sentence AS
SELECT
    s.id,
    ms.message_id,
    ms.platform_id,
    s.words,
    ms.score,
    s.len,
    ms.idx
FROM message_sentence ms
JOIN sentence s ON s.id = ms.sentence_id
JOIN message m ON m.id = ms.message_id
WHERE
    ms.score >= 0.8
    AND m.is_counted
    AND m.score > 0.1
    AND (
        s.len >= 3
        OR m.score >= 0.3
    );

CREATE MATERIALIZED VIEW non_tp_user_sentence AS
SELECT
    s.id,
    ms.message_id,
    ms.platform_id,
    s.words,
    ms.score,
    s.len,
    ms.idx
FROM message_sentence ms
JOIN sentence s
    ON s.id = ms.sentence_id
JOIN message m
    ON m.id = ms.message_id
WHERE
    ms.score < 0.8
    OR NOT m.is_counted
    OR m.score <= 0.1
    OR (
        s.len < 3
        AND m.score < 0.3
    );

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE attribute AS ENUM (
    'All',

    -- positions
    'Start',        -- starts from idx 0
    'End',          -- ends on idx -1
    'Full',         -- starts on idx 0 and ends on idx -1
    'Long',         -- in sentence with >= 4 words
    'Short',        -- in sentence with < 4 words
    'Inner',        -- does not start on idx 0 or end on idx -1

    -- discrete parts of speech
    'Subject',      -- before li
    'Verb',         -- after li and before e
    'Object',       -- after e and before prep
    'Prepositional Object', -- after prep

    -- functions
    'Head',         -- first word in any part of speech
    'Modifier',     -- following any head in the same part of speech
    'Preposition',  -- prep itself: tawa lon tan sama kepeken
    'Preverb',      -- preverb itself: kama awen lukin alasa ken wile sona
    'Noun',         -- subject or object or prep object
    'Particle',     -- TODO: probably duplicate with each particle

    -- more specific parts of speech
    'Transitive Verb', -- after li, with e
    'Intransitive Verb', -- after li, without e
    'Prepositional Verb' -- after li, is first prep+prep object
);


CREATE TABLE platform (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    _id smallint NOT NULL UNIQUE,
    name text NOT NULL
);


CREATE TABLE community (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    _id bigint NOT NULL,
    platform_id uuid NOT NULL REFERENCES platform (id),

    name text,

    num_sentences bigint NOT NULL DEFAULT 0,
    num_tp_sentences bigint NOT NULL DEFAULT 0,

    CONSTRAINT community__id_platform_unique
    UNIQUE (_id, platform_id)
);


CREATE TABLE author (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    _id bigint NOT NULL,
    platform_id uuid NOT NULL REFERENCES platform (id),

    name text NOT NULL,
    is_bot boolean NOT NULL,
    is_webhook boolean NOT NULL,

    num_sentences bigint NOT NULL DEFAULT 0,
    num_tp_sentences bigint NOT NULL DEFAULT 0,

    CONSTRAINT author__id_name_platform_unique
    UNIQUE (_id, platform_id)
);


CREATE TABLE message (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    _id bigint NOT NULL,
    author_id uuid NOT NULL REFERENCES author (id),
    community_id uuid NOT NULL REFERENCES community (id),
    container bigint NOT NULL,

    postdate timestamptz NOT NULL,
    content text NOT NULL,
    score double precision NOT NULL,
    is_counted boolean NOT NULL,

    CONSTRAINT message__id_community_unique
    UNIQUE (_id, community_id)
);
CREATE INDEX message_is_counted_postdate_idx
ON message (postdate)
WHERE is_counted = true;


CREATE TABLE sentence (
    -- tracks a unique sequence of words
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    words text[] NOT NULL UNIQUE,
    len integer NOT NULL
);
CREATE INDEX sentence_len_idx ON sentence (len);


CREATE TABLE message_sentence (
    message_id uuid NOT NULL REFERENCES message (id) ON DELETE CASCADE,
    sentence_id uuid NOT NULL REFERENCES sentence (id) ON DELETE CASCADE,
    idx integer NOT NULL, -- order of sentences in message
    -- sent scores can differ by context (not implemented as of 2026-10-25)
    score double precision NOT NULL,

    PRIMARY KEY (message_id, idx)
);
CREATE INDEX message_sentence_score_idx ON message_sentence (score);

/* NOTE:
 * everything beyond here is calculated from the above.
 * messages and sentences have been scored,
 * and sentences which are both is_counted and have a sufficient score
 * (i.e. which are able to appear in the tp_user_sentence m-view)
 * will be re-examined to find all their Terms */


CREATE TABLE term (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    text text NOT NULL UNIQUE,
    len smallint NOT NULL,
    hits bigint NOT NULL DEFAULT 0
  -- NOTE: all counted+sufficiently scored times the term was used; computed after ingest
);
CREATE INDEX term_hits_len_idx ON term (hits, len) INCLUDE (text); -- text fetchable from index
CREATE INDEX term_text_idx ON term (text);

CREATE TABLE term_author (
    -- unrolled from `term` to make unique authors countable
    term_id uuid NOT NULL REFERENCES term (id) ON DELETE CASCADE,
    author_id uuid NOT NULL REFERENCES author (id) ON DELETE CASCADE,
    hits bigint NOT NULL DEFAULT 0,
  -- NOTE: same as hits in term but only for this author using this term

    PRIMARY KEY (term_id, author_id)
);

CREATE TABLE frequency_context (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    community_id uuid NOT NULL REFERENCES community (id) ON DELETE CASCADE,
    day date NOT NULL,
    attr attribute NOT NULL,

    CONSTRAINT frequency_context_unique UNIQUE (community_id, day, attr)
);
CREATE INDEX frequency_context_idx
ON frequency_context (community_id, day, attr);


CREATE TABLE frequency (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    context_id uuid NOT NULL REFERENCES frequency_context (
        id
    ) ON DELETE CASCADE,
    term_id uuid NOT NULL REFERENCES term (id) ON DELETE CASCADE,
    hits bigint NOT NULL,

    CONSTRAINT frequency_context_term_unique
    UNIQUE (context_id, term_id)
);
CREATE INDEX frequency_term_idx ON frequency (term_id);
CREATE INDEX frequency_context_id_idx ON frequency (context_id);

CREATE TABLE frequency_author (
    frequency_id uuid NOT NULL REFERENCES frequency (id) ON DELETE CASCADE,
    author_id uuid NOT NULL REFERENCES author (id) ON DELETE CASCADE,
    hits bigint NOT NULL,
    -- NOTE: same as hits in term/term_author but now just in this context

    PRIMARY KEY (frequency_id, author_id)
);

CREATE MATERIALIZED VIEW tp_user_sentence AS
SELECT
    s.id,
    ms.message_id,
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
    AND m.is_counted;

/*
TODO: later

UPDATE author a
SET num_sentences = sub.cnt
FROM (
    SELECT m.author_id, COUNT(ms.sentence_id) AS cnt
    FROM message m
    JOIN message_sentence ms ON ms.message_id = m.id
    WHERE m.is_counted
    GROUP BY m.author_id
) sub
WHERE a.id = sub.author_id;

UPDATE author a
SET num_tp_sentences = sub.cnt
FROM (
    SELECT m.author_id, COUNT(*) AS cnt
    FROM tp_user_sentence tp
    JOIN message m ON m.id = tp.message_id
    GROUP BY m.author_id
) sub
WHERE a.id = sub.author_id;

UPDATE community c
SET num_sentences = sub.cnt
FROM (
    SELECT m.community_id, COUNT(ms.sentence_id) AS cnt
    FROM message m
    JOIN message_sentence ms ON ms.message_id = m.id
    WHERE m.is_counted
    GROUP BY m.community_id
) sub
WHERE c.id = sub.community_id;

UPDATE community c
SET num_tp_sentences = sub.cnt
FROM (
    SELECT m.community_id, COUNT(*) AS cnt
    FROM tp_user_sentence tp
    JOIN message m ON m.id = tp.message_id
    GROUP BY m.community_id
) sub
WHERE c.id = sub.community_id;

*/

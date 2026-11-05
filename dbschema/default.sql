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
    id int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    orig_id uuid NOT NULL,
    platform_id smallint NOT NULL REFERENCES platform (id),
    name text NOT NULL,

    CONSTRAINT orig_id_platform_id_unique_community UNIQUE (orig_id, platform_id)
);


CREATE TABLE author (
    id int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    orig_id uuid NOT NULL,
    platform_id smallint NOT NULL REFERENCES platform (id),
    name text NOT NULL,

    is_bot boolean NOT NULL,
    is_webhook boolean NOT NULL,

    CONSTRAINT orig_id_platform_id_unique_author UNIQUE (orig_id, platform_id)
);


CREATE TABLE message (
    id int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    orig_id uuid NOT NULL,
    platform_id smallint NOT NULL REFERENCES platform (id) ON DELETE CASCADE,
    author_id int NOT NULL REFERENCES author (id) ON DELETE CASCADE,
    community_id int NOT NULL REFERENCES community (id) ON DELETE CASCADE,
    container_id bigint NOT NULL, -- for levels of organization beyond community

    postdate timestamptz NOT NULL,
    content text NOT NULL,
    score real NOT NULL,
    is_counted boolean NOT NULL,

    CONSTRAINT orig_id_platform_id_unique_message UNIQUE (orig_id, platform_id)
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
    message_id int NOT NULL REFERENCES message(id) ON DELETE CASCADE,
    sentence_id int NOT NULL REFERENCES sentence (id) ON DELETE CASCADE,
    idx smallint NOT NULL, -- order of sentences in message
    score real NOT NULL,

    PRIMARY KEY (message_id, idx)
);
CREATE INDEX message_sentence_score_idx ON message_sentence (score);


CREATE MATERIALIZED VIEW community_sentence_stats AS
SELECT 
    c.id AS community_id,
    c.name AS community_name,
    COUNT(DISTINCT m.id) AS messages,
    COUNT(ms.sentence_id) AS sentences,
    COUNT(CASE WHEN ms.score >= 0.8 
          AND m.score >= 0.1 
          AND (s.len >= 3 OR m.score >= 0.3) 
          THEN ms.sentence_id 
          END) AS tp_sentences,
    COUNT(DISTINCT m.author_id) AS authors
FROM community c
JOIN message m ON c.id = m.community_id AND m.is_counted = true
LEFT JOIN message_sentence ms ON m.id = ms.message_id
LEFT JOIN sentence s ON ms.sentence_id = s.id
GROUP BY c.id, c.name;
-- CREATE UNIQUE INDEX community_sentence_stats_id_idx ON community_sentence_stats (community_id);

CREATE MATERIALIZED VIEW author_sentence_stats AS
SELECT 
    a.id AS author_id,
    a.name AS author_name,
    COUNT(DISTINCT m.id) AS messages,
    COUNT(ms.sentence_id) AS sentences,
    COUNT(CASE 
          WHEN ms.score >= 0.8 
          AND m.score >= 0.1 
          AND (s.len >= 3 OR m.score >= 0.3) 
          THEN 1 
          END) AS tp_sentences
    -- NOTE: I would put a community count here
    -- but it's useless outside Discord since authors are per-platform
FROM author a
JOIN message m ON a.id = m.author_id AND m.is_counted = true
LEFT JOIN message_sentence ms ON m.id = ms.message_id
LEFT JOIN sentence s ON ms.sentence_id = s.id
GROUP BY a.id, a.name;
-- CREATE UNIQUE INDEX author_sentence_stats_id_idx ON author_sentence_stats (author_id);




/* NOTE:
 * everything beyond here is calculated from the above.
 * messages and sentences have been scored,
 * and sentences which are both is_counted and have a sufficient score
 * (i.e. which are able to appear in the tp_user_sentence m-view)
 * will be re-examined to find all their Terms */


CREATE TABLE term (
    id int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    words text[] NOT NULL UNIQUE,
    len smallint GENERATED ALWAYS AS (cardinality(words)) STORED
);

CREATE TABLE context (
    id int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    community_id int NOT NULL REFERENCES community (id) ON DELETE CASCADE,
    day date NOT NULL,
    attr attribute NOT NULL,

    CONSTRAINT context_unique UNIQUE (community_id, day, attr)
);

CREATE TABLE context_author (
    id int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    context_id int NOT NULL REFERENCES context (id) ON DELETE CASCADE,
    author_id int NOT NULL REFERENCES author (id) ON DELETE CASCADE
);

CREATE TABLE frequency (
    context_author_id int NOT NULL REFERENCES context_author (id) ON DELETE CASCADE,
    term_id int NOT NULL REFERENCES term (id) ON DELETE CASCADE,
    hits int NOT NULL,

    PRIMARY KEY (context_author_id, term_id)
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
JOIN sentence s ON s.id = ms.sentence_id
JOIN message m ON m.id = ms.message_id
WHERE
    m.is_counted
    AND ms.score >= 0.8
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
JOIN sentence s ON s.id = ms.sentence_id
JOIN message m ON m.id = ms.message_id
WHERE
    m.is_counted AND
    (ms.score < 0.8
    OR m.score <= 0.1
    OR (
        s.len < 3
        AND m.score < 0.3
    ));

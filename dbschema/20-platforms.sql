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
    words text[] NOT NULL,
    words_hash bytea NOT NULL UNIQUE,
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

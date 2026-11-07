/* NOTE:
 * everything here is calculated from the content of ./20-platforms.sql
 * messages and sentences have been scored,
 * and sentences which are both is_counted and have a sufficient score
 * (i.e. which appear in the message_sentence_tp view)
 * will be re-examined to find all their Terms 
 */

CREATE TABLE term (
    id int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    words text[] NOT NULL UNIQUE,
    len smallint GENERATED ALWAYS AS (cardinality(words)) STORED
);
CREATE INDEX term_len_idx ON term (len, id);

CREATE TABLE context (
    id int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    community_id int NOT NULL REFERENCES community (id) ON DELETE CASCADE,
    day date NOT NULL,
    attr attribute NOT NULL,

    CONSTRAINT context_unique UNIQUE (community_id, day, attr)
);
CREATE INDEX context_attr_day_idx ON context (attr, day, id);

CREATE TABLE context_author (
    id int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    context_id int NOT NULL REFERENCES context (id) ON DELETE CASCADE,
    author_id int NOT NULL REFERENCES author (id) ON DELETE CASCADE,

    CONSTRAINT context_author_unique UNIQUE (context_id, author_id)
);

CREATE TABLE frequency (
    context_author_id int NOT NULL REFERENCES context_author (id) ON DELETE CASCADE,
    term_id int NOT NULL REFERENCES term (id) ON DELETE CASCADE,
    hits int NOT NULL,

    PRIMARY KEY (context_author_id, term_id)
);
CREATE INDEX frequency_term_idx ON frequency (term_id, context_author_id);

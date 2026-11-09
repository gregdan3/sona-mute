CREATE MATERIALIZED VIEW message_sentence_tp AS
SELECT
    ms.message_id,
    ms.sentence_id,
    ms.idx
FROM message_sentence ms
JOIN sentence s ON s.id = ms.sentence_id
JOIN message m ON m.id = ms.message_id
WHERE
    m.is_counted
    AND ms.score >= 0.8
    AND m.score > 0.1
    AND (s.len >= 3 OR m.score >= 0.3);
CREATE UNIQUE INDEX message_sentence_tp_pkey ON message_sentence_tp (message_id, idx);
CREATE INDEX message_sentence_tp_sentence_id_idx ON message_sentence_tp (sentence_id);

CREATE VIEW message_sentence_nontp AS
SELECT
    ms.message_id,
    ms.sentence_id,
    ms.idx
FROM message_sentence ms
JOIN sentence s ON s.id = ms.sentence_id
JOIN message m ON m.id = ms.message_id
WHERE
    m.is_counted AND
    (ms.score < 0.8
    OR m.score <= 0.1
    OR ( s.len < 3 AND m.score < 0.3));
-- CREATE UNIQUE INDEX message_sentence_nontp_pkey ON message_sentence_nontp (message_id, idx);
-- CREATE INDEX message_sentence_nontp_sentence_id_idx ON message_sentence_nontp (sentence_id);
-- this is essentially never used 

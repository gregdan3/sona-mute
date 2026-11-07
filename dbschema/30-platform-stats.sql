CREATE MATERIALIZED VIEW author_stats AS
SELECT 
    a.id AS author_id,
    a.name AS author_name,
    GREATEST(COUNT(DISTINCT m.community_id), 0) AS communities,
    GREATEST(COUNT(DISTINCT m.author_id), 0) AS authors,
    GREATEST(COUNT(DISTINCT m.id), 0) AS messages,
    GREATEST(COUNT(ms.sentence_id), 0) AS sentences,
    GREATEST(SUM(s.len), 0) AS words,
    GREATEST(COUNT(DISTINCT ms.sentence_id), 0) AS sentences_uniq,
    GREATEST(COUNT(mst.sentence_id), 0) AS sentences_tp,
    GREATEST(COUNT(DISTINCT mst.sentence_id), 0) AS sentences_uniq_tp,
    SUM(st.len) AS words_tp,
    ROUND(GREATEST(COUNT(mst.sentence_id)::numeric, 0) / GREATEST(COUNT(ms.sentence_id), 1) * 100, 1) AS pct_sentences_tp,
    ROUND(GREATEST(SUM(st.len)::numeric, 0) / GREATEST(SUM(s.len), 1) * 100, 1) AS pct_words_tp
FROM author a
JOIN message m ON a.id = m.author_id AND m.is_counted = true
LEFT JOIN message_sentence ms 
       ON m.id = ms.message_id
LEFT JOIN message_sentence_tp mst 
       ON ms.message_id  = mst.message_id 
      AND ms.idx = mst.idx
LEFT JOIN sentence s ON ms.sentence_id = s.id
LEFT JOIN sentence st ON mst.sentence_id = st.id
GROUP BY a.id, a.name;

CREATE MATERIALIZED VIEW community_stats AS
SELECT 
    c.id AS community_id,
    c.name AS community_name,
    GREATEST(COUNT(DISTINCT m.community_id), 0) AS communities,
    GREATEST(COUNT(DISTINCT m.author_id), 0) AS authors,
    GREATEST(COUNT(DISTINCT m.id), 0) AS messages,
    GREATEST(COUNT(ms.sentence_id), 0) AS sentences,
    GREATEST(SUM(s.len), 0) AS words,
    GREATEST(COUNT(DISTINCT ms.sentence_id), 0) AS sentences_uniq,
    GREATEST(COUNT(mst.sentence_id), 0) AS sentences_tp,
    GREATEST(COUNT(DISTINCT mst.sentence_id), 0) AS sentences_uniq_tp,
    SUM(st.len) AS words_tp,
    ROUND(GREATEST(COUNT(mst.sentence_id)::numeric, 0) / GREATEST(COUNT(ms.sentence_id), 1) * 100, 1) AS pct_sentences_tp,
    ROUND(GREATEST(SUM(st.len)::numeric, 0) / GREATEST(SUM(s.len), 1) * 100, 1) AS pct_words_tp
FROM community c
JOIN message m ON c.id = m.community_id AND m.is_counted = true
LEFT JOIN message_sentence ms ON m.id = ms.message_id
LEFT JOIN message_sentence_tp mst 
       ON ms.message_id  = mst.message_id 
      AND ms.idx = mst.idx
LEFT JOIN sentence s ON ms.sentence_id = s.id
LEFT JOIN sentence st ON mst.sentence_id = st.id
GROUP BY c.id, c.name;

CREATE MATERIALIZED VIEW monthly_stats AS
SELECT 
    DATE_TRUNC('MONTH', m.postdate) AS date,
    GREATEST(COUNT(DISTINCT m.community_id), 0) AS communities,
    GREATEST(COUNT(DISTINCT m.author_id), 0) AS authors,
    GREATEST(COUNT(DISTINCT m.id), 0) AS messages,
    GREATEST(COUNT(ms.sentence_id), 0) AS sentences,
    GREATEST(SUM(s.len), 0) AS words,
    GREATEST(COUNT(DISTINCT ms.sentence_id), 0) AS sentences_uniq,
    GREATEST(COUNT(mst.sentence_id), 0) AS sentences_tp,
    GREATEST(COUNT(DISTINCT mst.sentence_id), 0) AS sentences_uniq_tp,
    SUM(st.len) AS words_tp,
    ROUND(GREATEST(COUNT(mst.sentence_id)::numeric, 0) / GREATEST(COUNT(ms.sentence_id), 1) * 100, 1) AS pct_sentences_tp,
    ROUND(GREATEST(SUM(st.len)::numeric, 0) / GREATEST(SUM(s.len), 1) * 100, 1) AS pct_words_tp
FROM message m
LEFT JOIN message_sentence ms 
       ON m.id = ms.message_id
LEFT JOIN message_sentence_tp mst 
       ON ms.message_id  = mst.message_id 
      AND ms.idx = mst.idx
LEFT JOIN sentence s ON ms.sentence_id = s.id
LEFT JOIN sentence st ON mst.sentence_id = st.id
GROUP BY DATE_TRUNC('MONTH', m.postdate);

CREATE MATERIALIZED VIEW monthly_community_stats AS
SELECT 
    DATE_TRUNC('MONTH', m.postdate) AS date,
    c.id AS community_id,
    c.name AS community_name,
    GREATEST(COUNT(DISTINCT m.community_id), 0) AS communities,
    GREATEST(COUNT(DISTINCT m.author_id), 0) AS authors,
    GREATEST(COUNT(DISTINCT m.id), 0) AS messages,
    GREATEST(COUNT(ms.sentence_id), 0) AS sentences,
    GREATEST(SUM(s.len), 0) AS words,
    GREATEST(COUNT(DISTINCT ms.sentence_id), 0) AS sentences_uniq,
    GREATEST(COUNT(mst.sentence_id), 0) AS sentences_tp,
    GREATEST(COUNT(DISTINCT mst.sentence_id), 0) AS sentences_uniq_tp,
    SUM(st.len) AS words_tp,
    ROUND(GREATEST(COUNT(mst.sentence_id)::numeric, 0) / GREATEST(COUNT(ms.sentence_id), 1) * 100, 1) AS pct_sentences_tp,
    ROUND(GREATEST(SUM(st.len)::numeric, 0) / GREATEST(SUM(s.len), 1) * 100, 1) AS pct_words_tp
FROM message m
LEFT JOIN community c ON m.community_id = c.id
LEFT JOIN message_sentence ms 
       ON m.id = ms.message_id
LEFT JOIN message_sentence_tp mst 
       ON ms.message_id  = mst.message_id 
      AND ms.idx = mst.idx
LEFT JOIN sentence s ON ms.sentence_id = s.id
LEFT JOIN sentence st ON mst.sentence_id = st.id
GROUP BY DATE_TRUNC('MONTH', m.postdate), c.id, c.name;

CREATE MATERIALIZED VIEW yearly_stats AS
SELECT 
    (DATE_TRUNC('year', m.postdate - INTERVAL '7 months') + INTERVAL '7 months') AS date,
    GREATEST(COUNT(DISTINCT m.community_id), 0) AS communities,
    GREATEST(COUNT(DISTINCT m.author_id), 0) AS authors,
    GREATEST(COUNT(DISTINCT m.id), 0) AS messages,
    GREATEST(COUNT(ms.sentence_id), 0) AS sentences,
    GREATEST(SUM(s.len), 0) AS words,
    GREATEST(COUNT(DISTINCT ms.sentence_id), 0) AS sentences_uniq,
    GREATEST(COUNT(mst.sentence_id), 0) AS sentences_tp,
    GREATEST(COUNT(DISTINCT mst.sentence_id), 0) AS sentences_uniq_tp,
    SUM(st.len) AS words_tp,
    ROUND(GREATEST(COUNT(mst.sentence_id)::numeric, 0) / GREATEST(COUNT(ms.sentence_id), 1) * 100, 1) AS pct_sentences_tp,
    ROUND(GREATEST(SUM(st.len)::numeric, 0) / GREATEST(SUM(s.len), 1) * 100, 1) AS pct_words_tp
FROM message m
LEFT JOIN message_sentence ms 
       ON m.id = ms.message_id
LEFT JOIN message_sentence_tp mst 
       ON ms.message_id  = mst.message_id 
      AND ms.idx = mst.idx
LEFT JOIN sentence s ON ms.sentence_id = s.id
LEFT JOIN sentence st ON mst.sentence_id = st.id
GROUP BY (DATE_TRUNC('year', m.postdate - INTERVAL '7 months') + INTERVAL '7 months');


CREATE MATERIALIZED VIEW yearly_community_stats AS
SELECT 
    (DATE_TRUNC('year', m.postdate - INTERVAL '7 months') + INTERVAL '7 months') AS date,
    c.id AS community_id,
    c.name AS community_name,
    GREATEST(COUNT(DISTINCT m.community_id), 0) AS communities,
    GREATEST(COUNT(DISTINCT m.author_id), 0) AS authors,
    GREATEST(COUNT(DISTINCT m.id), 0) AS messages,
    GREATEST(COUNT(ms.sentence_id), 0) AS sentences,
    GREATEST(SUM(s.len), 0) AS words,
    GREATEST(COUNT(DISTINCT ms.sentence_id), 0) AS sentences_uniq,
    GREATEST(COUNT(mst.sentence_id), 0) AS sentences_tp,
    GREATEST(COUNT(DISTINCT mst.sentence_id), 0) AS sentences_uniq_tp,
    SUM(st.len) AS words_tp,
    ROUND(GREATEST(COUNT(mst.sentence_id)::numeric, 0) / GREATEST(COUNT(ms.sentence_id), 1) * 100, 1) AS pct_sentences_tp,
    ROUND(GREATEST(SUM(st.len)::numeric, 0) / GREATEST(SUM(s.len), 1) * 100, 1) AS pct_words_tp
FROM message m
LEFT JOIN community c ON m.community_id = c.id
LEFT JOIN message_sentence ms 
       ON m.id = ms.message_id
LEFT JOIN message_sentence_tp mst 
       ON ms.message_id  = mst.message_id 
      AND ms.idx = mst.idx
LEFT JOIN sentence s ON ms.sentence_id = s.id
LEFT JOIN sentence st ON mst.sentence_id = st.id
GROUP BY 
    (DATE_TRUNC('year', m.postdate - INTERVAL '7 months') + INTERVAL '7 months'),
    c.id,
    c.name;

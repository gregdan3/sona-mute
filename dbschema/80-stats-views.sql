CREATE MATERIALIZED VIEW author_stats AS
SELECT 
    a.id AS author_id,
    a.name AS author_name,
    COUNT(DISTINCT m.community_id) AS communities,
    COUNT(DISTINCT m.author_id) AS authors,
    COUNT(DISTINCT m.id) AS messages,
    COUNT(ms.sentence_id) AS sentences,
    SUM(s.len) AS words,
    COUNT(DISTINCT ms.sentence_id) AS sentences_uniq,
    COUNT(mst.sentence_id) AS sentences_tp,
    COUNT(DISTINCT mst.sentence_id) AS sentences_uniq_tp,
    SUM(st.len) AS words_tp,
    ROUND(COUNT(mst.sentence_id)::numeric / GREATEST(COUNT(ms.sentence_id), 1) * 100, 2) AS pct_sentences_tp,
    ROUND(SUM(st.len)::numeric / NULLIF(SUM(s.len), 0) * 100, 2) AS pct_words_tp
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
    COUNT(DISTINCT m.community_id) AS communities,
    COUNT(DISTINCT m.author_id) AS authors,
    COUNT(DISTINCT m.id) AS messages,
    COUNT(ms.sentence_id) AS sentences,
    SUM(s.len) AS words,
    COUNT(DISTINCT ms.sentence_id) AS sentences_uniq,
    COUNT(mst.sentence_id) AS sentences_tp,
    COUNT(DISTINCT mst.sentence_id) AS sentences_uniq_tp,
    SUM(st.len) AS words_tp,
    ROUND(COUNT(mst.sentence_id)::numeric / GREATEST(COUNT(ms.sentence_id), 1) * 100, 2) AS pct_sentences_tp,
    ROUND(SUM(st.len)::numeric / NULLIF(SUM(s.len), 0) * 100, 2) AS pct_words_tp
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
    COUNT(DISTINCT m.community_id) AS communities,
    COUNT(DISTINCT m.author_id) AS authors,
    COUNT(DISTINCT m.id) AS messages,
    COUNT(ms.sentence_id) AS sentences,
    SUM(s.len) AS words,
    COUNT(DISTINCT ms.sentence_id) AS sentences_uniq,
    COUNT(mst.sentence_id) AS sentences_tp,
    COUNT(DISTINCT mst.sentence_id) AS sentences_uniq_tp,
    SUM(st.len) AS words_tp,
    ROUND(COUNT(mst.sentence_id)::numeric / GREATEST(COUNT(ms.sentence_id), 1) * 100, 2) AS pct_sentences_tp,
    ROUND(SUM(st.len)::numeric / NULLIF(SUM(s.len), 0) * 100, 2) AS pct_words_tp
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
    COUNT(DISTINCT m.community_id) AS communities,
    COUNT(DISTINCT m.author_id) AS authors,
    COUNT(DISTINCT m.id) AS messages,
    COUNT(ms.sentence_id) AS sentences,
    SUM(s.len) AS words,
    COUNT(DISTINCT ms.sentence_id) AS sentences_uniq,
    COUNT(mst.sentence_id) AS sentences_tp,
    COUNT(DISTINCT mst.sentence_id) AS sentences_uniq_tp,
    SUM(st.len) AS words_tp,
    ROUND(COUNT(mst.sentence_id)::numeric / GREATEST(COUNT(ms.sentence_id), 1) * 100, 2) AS pct_sentences_tp,
    ROUND(SUM(st.len)::numeric / NULLIF(SUM(s.len), 0) * 100, 2) AS pct_words_tp
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
    COUNT(DISTINCT m.community_id) AS communities,
    COUNT(DISTINCT m.author_id) AS authors,
    COUNT(DISTINCT m.id) AS messages,
    COUNT(ms.sentence_id) AS sentences,
    SUM(s.len) AS words,
    COUNT(DISTINCT ms.sentence_id) AS sentences_uniq,
    COUNT(mst.sentence_id) AS sentences_tp,
    COUNT(DISTINCT mst.sentence_id) AS sentences_uniq_tp,
    SUM(st.len) AS words_tp,
    ROUND(COUNT(mst.sentence_id)::numeric / GREATEST(COUNT(ms.sentence_id), 1) * 100, 2) AS pct_sentences_tp,
    ROUND(SUM(st.len)::numeric / NULLIF(SUM(s.len), 0) * 100, 2) AS pct_words_tp
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
    COUNT(DISTINCT m.community_id) AS communities,
    COUNT(DISTINCT m.author_id) AS authors,
    COUNT(DISTINCT m.id) AS messages,
    COUNT(ms.sentence_id) AS sentences,
    SUM(s.len) AS words,
    COUNT(DISTINCT ms.sentence_id) AS sentences_uniq,
    COUNT(mst.sentence_id) AS sentences_tp,
    COUNT(DISTINCT mst.sentence_id) AS sentences_uniq_tp,
    SUM(st.len) AS words_tp,
    ROUND(COUNT(mst.sentence_id)::numeric / GREATEST(COUNT(ms.sentence_id), 1) * 100, 2) AS pct_sentences_tp,
    ROUND(SUM(st.len)::numeric / NULLIF(SUM(s.len), 0) * 100, 2) AS pct_words_tp
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

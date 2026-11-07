CREATE VIEW monthly AS
SELECT
    t.words AS term,
    t.len,
    x.attr,
    x.day,
    x.hits,
    x.authors,
    x.hits_nt,
    x.authors_nt,
    x.communities
FROM (
    SELECT
        f.term_id,
        c.attr,
        date_trunc('month', c.day) AS day,
        sum(f.hits) AS hits,
        count(DISTINCT ca.author_id) AS authors,
        sum(f.hits) FILTER (WHERE ast.sentences_tp >= 20) AS hits_nt,
        count(DISTINCT ca.author_id) FILTER (WHERE ast.sentences_tp >= 20)
            AS authors_nt,
        count(DISTINCT c.community_id) AS communities
    FROM frequency f
    JOIN context_author ca ON f.context_author_id = ca.id
    JOIN context c ON ca.context_id = c.id
    JOIN author_stats ast ON ca.author_id = ast.author_id
    GROUP BY
        f.term_id,
        c.attr,
        date_trunc('month', c.day)
) x
JOIN term t ON x.term_id = t.id;

CREATE VIEW total_monthly AS
SELECT
    t.len,
    c.attr,
    date_trunc('month', c.day) AS day,
    sum(f.hits) AS hits,
    count(DISTINCT ca.author_id) AS authors,
    sum(f.hits) FILTER (WHERE ast.sentences_tp >= 20) AS hits_nt,
    count(DISTINCT ca.author_id) FILTER (WHERE ast.sentences_tp >= 20)
        AS authors_nt,
    count(DISTINCT c.community_id) AS communities
FROM frequency f
JOIN context_author ca ON f.context_author_id = ca.id
JOIN context c ON ca.context_id = c.id
JOIN term t ON f.term_id = t.id
JOIN author_stats ast ON ca.author_id = ast.author_id
GROUP BY
    t.len,
    c.attr,
    date_trunc('month', c.day);


CREATE VIEW yearly AS
SELECT
    t.words AS term,
    t.len,
    x.attr,
    x.day,
    x.hits,
    x.authors,
    x.hits_nt,
    x.authors_nt,
    x.communities
FROM (
    SELECT
        f.term_id,
        c.attr,
        date_trunc('year', c.day - INTERVAL '7 months')
        + INTERVAL '7 months' AS day,
        sum(f.hits) AS hits,
        count(DISTINCT ca.author_id) AS authors,
        sum(f.hits) FILTER (WHERE ast.sentences_tp >= 20) AS hits_nt,
        count(DISTINCT ca.author_id) FILTER (WHERE ast.sentences_tp >= 20)
            AS authors_nt,
        count(DISTINCT c.community_id) AS communities
    FROM frequency f
    JOIN context_author ca ON f.context_author_id = ca.id
    JOIN context c ON ca.context_id = c.id
    JOIN author_stats ast ON ca.author_id = ast.author_id
    GROUP BY
        f.term_id,
        c.attr,
        date_trunc('year', c.day - INTERVAL '7 months')
        + INTERVAL '7 months'
) x
JOIN term t ON x.term_id = t.id;

CREATE VIEW total_yearly AS
SELECT
    t.len,
    c.attr,
    (
        date_trunc('year', c.day - INTERVAL '7 months')
        + INTERVAL '7 months'
    ) AS day,
    sum(f.hits) AS hits,
    count(DISTINCT ca.author_id) AS authors,
    sum(f.hits) FILTER (WHERE ast.sentences_tp >= 20) AS hits_nt,
    count(DISTINCT ca.author_id) FILTER (WHERE ast.sentences_tp >= 20)
        AS authors_nt,
    count(DISTINCT c.community_id) AS communities
FROM frequency f
JOIN context_author ca ON f.context_author_id = ca.id
JOIN context c ON ca.context_id = c.id
JOIN term t ON f.term_id = t.id
JOIN author_stats ast ON ca.author_id = ast.author_id
GROUP BY
    t.len,
    c.attr,
    (
        date_trunc('year', c.day - INTERVAL '7 months')
        + INTERVAL '7 months'
    );


CREATE VIEW alltime AS
SELECT
    t.words AS term,
    t.len,
    x.attr,
    x.hits,
    x.authors,
    x.hits_nt,
    x.authors_nt,
    x.communities
FROM (
    SELECT
        f.term_id,
        c.attr,
        sum(f.hits) AS hits,
        count(DISTINCT ca.author_id) AS authors,
        sum(f.hits) FILTER (WHERE ast.sentences_tp >= 20) AS hits_nt,
        count(DISTINCT ca.author_id) FILTER (WHERE ast.sentences_tp >= 20)
            AS authors_nt,
        count(DISTINCT c.community_id) AS communities
    FROM frequency f
    JOIN context_author ca ON f.context_author_id = ca.id
    JOIN context c ON ca.context_id = c.id
    JOIN author_stats ast ON ca.author_id = ast.author_id
    GROUP BY
        f.term_id,
        c.attr
) x
JOIN term t ON x.term_id = t.id;


CREATE VIEW total_alltime AS
SELECT
    t.len,
    c.attr,
    sum(f.hits) AS hits,
    count(DISTINCT ca.author_id) AS authors,
    sum(f.hits) FILTER (WHERE ast.sentences_tp >= 20) AS hits_nt,
    count(DISTINCT ca.author_id) FILTER (WHERE ast.sentences_tp >= 20)
        AS authors_nt,
    count(DISTINCT c.community_id) AS communities
FROM frequency f
JOIN context_author ca ON f.context_author_id = ca.id
JOIN context c ON ca.context_id = c.id
JOIN term t ON f.term_id = t.id
JOIN author_stats ast ON ca.author_id = ast.author_id
GROUP BY
    t.len,
    c.attr;

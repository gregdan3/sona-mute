CREATE VIEW monthly AS
SELECT
    x.term_id,
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
    x.term_id,
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
    x.term_id,
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

/* NOTE: the rest of this is experimental.
 */

-- shannon entropy
CREATE VIEW shannon_entropy AS
WITH author_terms AS (
    SELECT
        ca.author_id,
        t.len,
        -- c.attr,
        f.term_id,
        sum(f.hits)::double precision AS hits
    FROM frequency f
    JOIN context_author ca ON f.context_author_id = ca.id
    JOIN context c ON ca.context_id = c.id
    JOIN term t ON f.term_id = t.id
    WHERE c.attr = 'All'
    GROUP BY
        ca.author_id,
        t.len,
        -- c.attr,
        f.term_id
),

author_entropy AS (
    SELECT
        author_id,
        len,
        -- attr,
        count(*) AS terms,
        sum(hits) AS hits,
        sum(
            -(hits / total_hits) * ln(hits / total_hits)
        ) AS entropy
    FROM (
        SELECT
            *,
            sum(hits) OVER (
                PARTITION BY author_id, len -- , attr
            ) AS total_hits
        FROM author_terms
    ) x
    GROUP BY
        author_id,
        len -- ,
        -- attr
)

SELECT
    a.name,
    x.len,
    -- x.attr,
    x.terms,
    x.hits,
    exp(x.entropy) AS effective_terms
FROM author_entropy x
JOIN author a ON x.author_id = a.id
ORDER BY
    x.len,
    -- x.attr,
    effective_terms DESC;

select
    DATE_TRUNC('month', postdate),
    COUNT(1)
from message
group by DATE_TRUNC('month', postdate)
order by DATE_TRUNC('month', postdate) asc;


select
    DATE_TRUNC('month', postdate),
    c.name,
    COUNT(1) as sents,
    COUNT(case when s.score >= 0.8 then 1 else NULL end) as tp_sents,
    COUNT(case when s.score < 0.8 then 1 else NULL end) as nontp_sents
from message m
join message_sentence s on m.id = s.message_id and m.platform_id = s.platform_id
join community c on m.community_id = c.id and m.platform_id = c.platform_id
group by DATE_TRUNC('month', postdate), c.name
order by DATE_TRUNC('month', postdate) asc;

select
    idx,
    COUNT(1)
from message_sentence ms
join message m on ms.message_id = m.id and ms.platform_id = m.platform_id
where ms.score >= 0.8
group by idx
order by idx asc;

select
    a.id,
    a.platform_id,
    a.name,
    m.score,
    AVG(ms.score),
    m.postdate
from message m
join author a on m.author_id = a.id and m.platform_id = a.platform_id
join
    message_sentence ms
    on m.id = ms.message_id and m.platform_id = ms.platform_id
where idx = (select MAX(idx) from message_sentence);

select
    -- t.words as term,
    -- c.attr,
    c.day,
    SUM(f.hits) as hits,
    COUNT(distinct ca.author_id) as authors
from frequency f
join context_author ca on f.context_author_id = ca.id
join context c on ca.context_id = c.id
join term t on f.term_id = t.id
where
    c.attr = 'All'::attribute
    and t.len = 1
group by
    c.day
-- t.words,
-- c.attr
order by c.day asc;

select
    a.id as author_id,
    a.name as author_name,
    t.words as term,
    SUM(f.hits) as hits
from frequency f
join context_author ca on f.context_author_id = ca.id
join author a on ca.author_id = a.id
join context c on ca.context_id = c.id
join term t on f.term_id = t.id
where
    c.attr = 'All'::attribute
    and t.len = 1
group by a.id, a.name, t.id, t.words
having SUM(f.hits) >= 10
order by hits desc;


select
    a.name,
    x.terms,
    x.hits,
    x.communities
from (
    select
        ca.author_id,
        COUNT(distinct f.term_id) as terms,
        SUM(f.hits) as hits,
        COUNT(distinct c.community_id) as communities
    from frequency f
    join context_author ca on f.context_author_id = ca.id
    join context c on ca.context_id = c.id
    -- join author_stats ast on ca.author_id = ast.author_id
    join term t on f.term_id = t.id
    where
        c.attr = 'All' and t.len = 1
    group by
        ca.author_id
) x
join author a on x.author_id = a.id
where hits >= 1000
order by
    x.terms desc
limit 500


-- this is shannon entropy
WITH author_terms AS (
    SELECT
        ca.author_id,
        t.len,
        -- c.attr,
        f.term_id,
        SUM(f.hits)::double precision AS hits
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
        COUNT(*) AS terms,
        SUM(hits) AS hits,
        SUM(
            -(hits / total_hits) * LN(hits / total_hits)
        ) AS entropy
    FROM (
        SELECT
            *,
            SUM(hits) OVER (
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
    EXP(x.entropy) AS effective_terms
FROM author_entropy x
JOIN author a ON x.author_id = a.id
WHERE x.hits >= 1000
ORDER BY
    x.len,
    -- x.attr,
    effective_terms DESC
limit 1000;

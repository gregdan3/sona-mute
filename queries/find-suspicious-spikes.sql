WITH base AS (
    SELECT
        m.term_id,
        t.text,
        t.len,
        m.attr,
        m.day,
        m.hits,
        1.0 * m.hits / tm.hits AS rel
    FROM monthly m
    JOIN term t ON t.id = m.term_id
    JOIN total_monthly tm ON tm.day = m.day
    WHERE
    -- mimic ilo Muni's % based searching
        m.attr = 1 AND tm.attr = 1 AND tm.term_len = 1
-- AND t.len <= 4
),

neighbors AS (
    SELECT
        a.term_id,
        a.attr,
        a.day,
        a.hits,
        a.rel,

        b.hits AS neighbor_hits,
        b.rel AS neighbor_rel,

        ABS(b.day - a.day) AS distance,

        ROW_NUMBER() OVER (
            PARTITION BY a.term_id, a.attr, a.day
            ORDER BY ABS(b.day - a.day)
        ) AS rn

    FROM base a
    JOIN base b
        ON
            a.term_id = b.term_id
            AND a.attr = b.attr
            AND a.day != b.day
),

nearest4 AS (
    SELECT *
    FROM neighbors
    WHERE rn <= 4
),

averaged AS (
    SELECT
        term_id,
        attr,
        day,
        hits,
        rel,
        AVG(neighbor_hits) AS neighbor_avg_hits,
        AVG(neighbor_rel) AS neighbor_avg_rel,
        COUNT(*) AS neighbor_count
    FROM nearest4
    GROUP BY term_id, attr, day, hits, rel
)

SELECT
    DATE(a.day, 'unixepoch') AS date,
    t.text,
    a.hits,
    a.rel,
    a.hits / a.neighbor_avg_hits AS spike_ratio_hits,
    a.rel / a.neighbor_avg_rel AS spike_ratio_rel
FROM averaged a
JOIN term t ON t.id = a.term_id
WHERE
    a.neighbor_count = 4
    AND a.neighbor_avg_hits > 0
    AND a.neighbor_avg_rel > 0

    AND (
        a.hits >= 5 * a.neighbor_avg_hits
        OR a.rel >= 5 * a.neighbor_avg_rel
    )

    -- noise filter for detected spike
    AND a.hits >= 40
    -- only look at 2017 forward
    AND a.day >= 1483200000
ORDER BY day ASC;

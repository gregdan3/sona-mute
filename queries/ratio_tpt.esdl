SELECT Author {
  _id,
  name,
  sents := count(.<author[is Message].sentences),
  tpt_sents := count( .<author[is Message].sentences FILTER .score >= 0.8),
  ratio := (
      IF count(.<author[is Message].sentences) != 0 THEN
          count( .<author[is Message].sentences FILTER .score >= 0.8) 
          / count(.<author[is Message].sentences)
      ELSE 0
  )
} ORDER BY .ratio;

# WITH
#     A := Author,
#     M := A.<author[is Message].sentences,
#     total_sents := count(M),
#     tpt_sents := count(M FILTER .score >= 0.8)
# SELECT A {
#     _id,
#     name,
#     sents := total_sents,
#     tpt_sents := tpt_sents,
#     ratio := (IF total_sents != 0 THEN tpt_sents / total_sents ELSE 0)
# } LIMIT 10;

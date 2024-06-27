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

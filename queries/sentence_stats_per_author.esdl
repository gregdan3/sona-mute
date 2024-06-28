SELECT Author {
  _id,
  name,
  sents := count(.user_messages.sentences),
  tpt_sents := count(.user_messages.tp_sentences),
  ratio := (count(.user_messages.tp_sentences) / count(.user_messages.sentences))
} FILTER count(.user_messages.sentences) > 0
ORDER BY .ratio;

SELECT Author {
  _id,
  name,
  tpt_sents := count(.user_messages.tp_sentences)
} FILTER ._id = 1;


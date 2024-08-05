select distinct TPUserSentence {
  _id := .message._id,
  commname := .message.community.name,
  channel := .message.container,
  authname := .message.author.name,
  date := .message.postdate,
  content := .message.content
} filter contains(.words, 'ka')
order by (.date);

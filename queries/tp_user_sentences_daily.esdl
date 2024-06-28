SELECT count(
  TPUserSentence FILTER
    .message.postdate >= <datetime>'2024-05-16T00:00:00+00:00' AND
    .message.postdate < <datetime>'2024-05-17T00:00:00+00:00'
);

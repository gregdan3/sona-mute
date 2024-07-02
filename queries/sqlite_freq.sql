select word_id, sum(occurrences) as n from word_freq where min_len = 5 group by word order by n;
select phrase, sum(occurrences) as n from phrase_freq where length = 5 group by phrase order by n;

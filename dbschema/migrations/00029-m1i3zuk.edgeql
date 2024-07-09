CREATE MIGRATION m1i3zukt7y6pq7fupiffclzbsf3ujcj6jvqyk7phrplw332jfg7oba
    ONTO m1uvvnewrah7rzgro2k7sl6utaq3kmgjuencrsmlwwjipto4ynpcdq
{
  CREATE TYPE default::Frequency {
      CREATE REQUIRED LINK community: default::Community;
      CREATE REQUIRED PROPERTY day: std::datetime;
      CREATE REQUIRED PROPERTY min_sent_len: std::int64;
      CREATE REQUIRED PROPERTY text: std::str;
      CREATE CONSTRAINT std::exclusive ON ((.text, .min_sent_len, .community, .day));
      CREATE INDEX ON (.community);
      CREATE REQUIRED PROPERTY phrase_len: std::int64;
      CREATE INDEX ON (.phrase_len);
      CREATE INDEX ON (.day);
      CREATE INDEX ON (.min_sent_len);
      CREATE REQUIRED PROPERTY occurrences: std::int64;
  };
};

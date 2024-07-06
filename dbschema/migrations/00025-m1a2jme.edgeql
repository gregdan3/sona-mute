CREATE MIGRATION m1a2jme3yvsboayaj6tqp3zx7evgb5kre2ium4rih3tp6f7iivdvbq
    ONTO m17ifur4bn7ahb6wbtg5owei4lhoawv47w7wanwsnug7vhkfkvckcq
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

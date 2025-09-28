CREATE MIGRATION m1l2ahl42renvltuudrr6y63nmgnufbd6b3w6pjyg773jeswbnjj5q
    ONTO m1rdwczvcu4uj2zcejaeqwkskumzc6t3se7t4zflejvkzt6mhyeina
{
  CREATE SCALAR TYPE default::FrequencyType EXTENDING enum<All, SentenceStart, SentenceEnd>;
  ALTER TYPE default::Frequency {
      CREATE REQUIRED PROPERTY type: default::FrequencyType {
          SET REQUIRED USING (default::FrequencyType.All);
      };
  };
  ALTER TYPE default::Frequency {
      CREATE CONSTRAINT std::exclusive ON ((.term, .type, .community, .min_sent_len, .day));
  };
  ALTER TYPE default::Frequency {
      DROP CONSTRAINT std::exclusive ON ((.term, .community, .min_sent_len, .day));
  };
  ALTER TYPE default::Term {
      DROP INDEX ON ((.total_hits, .len, .marked));
  };
  ALTER TYPE default::Term {
      CREATE INDEX ON ((.total_hits, .len));
  };
  ALTER TYPE default::Term {
      DROP INDEX ON (.text);
  };
  ALTER TYPE default::Term {
      CREATE INDEX ON ((.text, .len));
  };
  ALTER TYPE default::Term {
      DROP INDEX ON ((.total_hits, .text, .len));
  };
  ALTER TYPE default::Term {
      CREATE MULTI LINK total_authors: default::Author;
  };
  ALTER TYPE default::Term {
      DROP PROPERTY marked;
  };
};

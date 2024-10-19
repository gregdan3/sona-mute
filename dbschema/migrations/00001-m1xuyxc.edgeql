CREATE MIGRATION m1xuyxchpkcyuktxo76gpu3in2ecz7bczshcrhjlu76yokbzo3aooa
    ONTO initial
{
  CREATE TYPE default::Message {
      CREATE REQUIRED PROPERTY is_counted: std::bool;
      CREATE REQUIRED PROPERTY _id: std::bigint;
      CREATE REQUIRED PROPERTY postdate: std::datetime;
      CREATE INDEX ON ((.is_counted, .postdate));
      CREATE REQUIRED PROPERTY container: std::bigint;
      CREATE REQUIRED PROPERTY content: std::str;
  };
  CREATE TYPE default::Sentence {
      CREATE REQUIRED LINK message: default::Message;
      CREATE REQUIRED PROPERTY score: std::float64;
      CREATE REQUIRED PROPERTY words: array<std::str>;
      CREATE INDEX ON (.score);
  };
  CREATE ALIAS default::NonTPUserSentence := (
      SELECT
          default::Sentence
      FILTER
          ((.score < 0.8) AND .message.is_counted)
  );
  CREATE ALIAS default::TPUserSentence := (
      SELECT
          default::Sentence
      FILTER
          ((.score >= 0.8) AND .message.is_counted)
  );
  CREATE TYPE default::Platform {
      CREATE REQUIRED PROPERTY _id: std::int16;
      CREATE CONSTRAINT std::exclusive ON (._id);
      CREATE INDEX ON (._id);
      CREATE REQUIRED PROPERTY name: std::str;
  };
  CREATE TYPE default::Author {
      CREATE REQUIRED LINK platform: default::Platform;
      CREATE REQUIRED PROPERTY _id: std::bigint;
      CREATE PROPERTY name: std::str;
      CREATE CONSTRAINT std::exclusive ON ((._id, .name, .platform));
      CREATE INDEX ON ((._id, .platform));
      CREATE REQUIRED PROPERTY is_bot: std::bool;
      CREATE REQUIRED PROPERTY is_webhook: std::bool;
  };
  ALTER TYPE default::Message {
      CREATE REQUIRED LINK author: default::Author;
  };
  ALTER TYPE default::Author {
      CREATE MULTI LINK messages := (.<author[IS default::Message]);
      CREATE MULTI LINK user_messages := (SELECT
          .<author[IS default::Message]
      FILTER
          .is_counted
      );
  };
  CREATE TYPE default::Term {
      CREATE REQUIRED PROPERTY text: std::str;
      CREATE CONSTRAINT std::exclusive ON (.text);
      CREATE REQUIRED PROPERTY len: std::int16;
      CREATE INDEX ON ((.text, .len));
  };
  CREATE TYPE default::Frequency {
      CREATE REQUIRED MULTI LINK authors: default::Author;
      CREATE REQUIRED LINK term: default::Term;
      CREATE REQUIRED PROPERTY day: std::datetime;
      CREATE REQUIRED PROPERTY min_sent_len: std::int16;
      CREATE INDEX ON ((.term, .min_sent_len, .day));
      CREATE REQUIRED PROPERTY hits: std::int64;
  };
  CREATE TYPE default::Community {
      CREATE REQUIRED LINK platform: default::Platform;
      CREATE REQUIRED PROPERTY _id: std::bigint;
      CREATE CONSTRAINT std::exclusive ON ((._id, .platform));
      CREATE INDEX ON ((._id, .platform));
      CREATE PROPERTY name: std::str;
  };
  ALTER TYPE default::Message {
      CREATE REQUIRED LINK community: default::Community;
      CREATE CONSTRAINT std::exclusive ON ((._id, .community));
      CREATE INDEX ON ((._id, .community));
      CREATE MULTI LINK sentences := (.<message[IS default::Sentence]);
      CREATE MULTI LINK tp_sentences := (SELECT
          .<message[IS default::Sentence]
      FILTER
          (.score >= 0.8)
      );
  };
  ALTER TYPE default::Community {
      CREATE MULTI LINK messages := (.<community[IS default::Message]);
      CREATE MULTI LINK user_messages := (SELECT
          .<community[IS default::Message]
      FILTER
          .is_counted
      );
  };
  ALTER TYPE default::Frequency {
      CREATE REQUIRED LINK community: default::Community;
      CREATE CONSTRAINT std::exclusive ON ((.term, .community, .min_sent_len, .day));
  };
};

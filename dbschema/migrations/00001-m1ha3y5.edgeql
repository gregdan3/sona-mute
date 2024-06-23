CREATE MIGRATION m1ha3y57pahg6hdzq2mogvl7bdlmshbi3f7bkqxtvyfyrlavhzof7q
    ONTO initial
{
  CREATE TYPE default::Platform {
      CREATE REQUIRED PROPERTY _id: std::int64;
      CREATE CONSTRAINT std::exclusive ON (._id);
      CREATE INDEX ON (._id);
      CREATE REQUIRED PROPERTY name: std::str;
  };
  CREATE TYPE default::Author {
      CREATE REQUIRED LINK platform: default::Platform;
      CREATE REQUIRED PROPERTY _id: std::int64;
      CREATE CONSTRAINT std::exclusive ON ((._id, .platform));
      CREATE INDEX ON ((._id, .platform));
      CREATE REQUIRED PROPERTY name: std::str;
  };
  CREATE TYPE default::Community {
      CREATE REQUIRED LINK platform: default::Platform;
      CREATE REQUIRED PROPERTY _id: std::int64;
      CREATE CONSTRAINT std::exclusive ON ((._id, .platform));
      CREATE INDEX ON ((._id, .platform));
      CREATE REQUIRED PROPERTY name: std::str;
  };
  CREATE TYPE default::Message {
      CREATE REQUIRED LINK author: default::Author;
      CREATE REQUIRED LINK community: default::Community;
      CREATE REQUIRED PROPERTY _id: std::int64;
      CREATE CONSTRAINT std::exclusive ON ((._id, .community));
      CREATE INDEX ON ((._id, .community));
      CREATE PROPERTY container: std::int64;
      CREATE REQUIRED PROPERTY content: std::str;
      CREATE REQUIRED PROPERTY postdate: std::datetime;
  };
  CREATE TYPE default::Sentence {
      CREATE REQUIRED LINK message: default::Message;
      CREATE REQUIRED PROPERTY score: std::float64;
      CREATE REQUIRED PROPERTY words: array<std::str>;
  };
  ALTER TYPE default::Message {
      CREATE MULTI LINK sentences := (.<message[IS default::Sentence]);
  };
};

CREATE MIGRATION m1nkonpbl5da63t7mobdckxaqwsqn4k54e3aqvoy6h3e7vfvow7paa
    ONTO m1kpoey4a7xdaurl2i4bqb4pl3csjqy6afamayl3bu23r4myuv6evq
{
  ALTER TYPE default::Author {
      ALTER LINK platform {
          RESET readonly;
      };
      ALTER PROPERTY _id {
          RESET readonly;
      };
  };
  ALTER TYPE default::Community {
      ALTER LINK platform {
          RESET readonly;
      };
      ALTER PROPERTY _id {
          RESET readonly;
      };
  };
  ALTER TYPE default::Frequency {
      ALTER LINK community {
          RESET readonly;
      };
      ALTER LINK term {
          RESET readonly;
      };
      ALTER PROPERTY day {
          RESET readonly;
      };
      ALTER PROPERTY min_sent_len {
          RESET readonly;
      };
  };
  ALTER TYPE default::Sentence {
      ALTER LINK message {
          RESET readonly;
      };
      ALTER PROPERTY words {
          RESET readonly;
      };
  };
  ALTER TYPE default::Platform {
      ALTER PROPERTY _id {
          RESET readonly;
      };
      ALTER PROPERTY name {
          RESET readonly;
      };
  };
  ALTER TYPE default::Term {
      ALTER PROPERTY len {
          RESET readonly;
      };
      ALTER PROPERTY text {
          RESET readonly;
      };
  };
};

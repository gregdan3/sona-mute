CREATE MIGRATION m12gvncow7emv6w5zkyrzn3vrxmqp4bp5osrjjssyvpmf23lgejimq
    ONTO m15yaslskfnljjofmazwbdyszao6xzak2i4nzyvvprngz2ewlljd3a
{
  ALTER TYPE default::Message {
      CREATE REQUIRED PROPERTY is_counted: std::bool {
          SET REQUIRED USING (<std::bool>{true});
      };
  };
  ALTER ALIAS default::NonTPUserSentence USING (SELECT
      default::Sentence
  FILTER
      ((.score < 0.8) AND .message.is_counted)
  );
  ALTER ALIAS default::TPUserSentence USING (SELECT
      default::Sentence
  FILTER
      ((.score >= 0.8) AND .message.is_counted)
  );
  ALTER TYPE default::Author {
      DROP INDEX ON (.is_bot);
      DROP INDEX ON (.is_webhook);
      ALTER LINK user_messages {
          USING (SELECT
              .<author[IS default::Message]
          FILTER
              .is_counted
          );
      };
  };
  ALTER TYPE default::Community {
      ALTER LINK user_messages {
          USING (SELECT
              .<community[IS default::Message]
          FILTER
              .is_counted
          );
      };
  };
};

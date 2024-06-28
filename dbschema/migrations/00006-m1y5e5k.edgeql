CREATE MIGRATION m1y5e5kcoiwmvyefwvtiu6wb5ivdeubxkunqjuotwc2dsa6rvqug2a
    ONTO m17acxbzc4qluwbfa7c7mwsq2xlsm7eqqcesrapuici3qlwubkj2ta
{
  DROP ALIAS default::TPSentence;
  DROP ALIAS default::UserMessage;
  ALTER TYPE default::Author {
      CREATE MULTI LINK messages := (.<author[IS default::Message]);
      CREATE MULTI LINK user_messages := (SELECT
          .<author[IS default::Message]
      FILTER
          ((.author.is_bot = .author.is_webhook) AND NOT ((.container IN {316066233755631616, 786041291707777034, 914305039764426772, 1128714905932021821})))
      );
  };
  ALTER TYPE default::Message {
      CREATE MULTI LINK tp_sentences := (SELECT
          .<message[IS default::Sentence]
      FILTER
          (.score >= 0.8)
      );
  };
};

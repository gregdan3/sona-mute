CREATE MIGRATION m1dyouhrylngqp2crmtvfmmrrdwgglo6urnnzbssdu5er55q6mjfoq
    ONTO m1lji6ax23jfkibtdwfgdpwh4bmgr4m2zyotuhwvk6c27jjs66odoq
{
  CREATE ALIAS default::TPSentence := (
      SELECT
          default::Sentence
      FILTER
          (.score >= 0.8)
  );
  CREATE ALIAS default::UserMessage := (
      SELECT
          default::Message
      FILTER
          ((.author.is_bot = .author.is_webhook) AND NOT ((.container IN {316066233755631616, 786041291707777034, 914305039764426772, 1128714905932021821})))
  );
  CREATE ALIAS default::TPUserSentence := (
      SELECT
          default::TPSentence
      FILTER
          (.message IN default::UserMessage)
  );
};

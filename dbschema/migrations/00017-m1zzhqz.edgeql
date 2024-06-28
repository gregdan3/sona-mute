CREATE MIGRATION m1zzhqzcf26cev46tmnekngkxwyym6o2q4yox2tw2vkpo3qvfnnyta
    ONTO m1rqmlqjo36du2uprl34y5ghexwlzz62t55g6x4d2ivayes2fzqlmq
{
  CREATE ALIAS default::TPUserSentence := (
      SELECT
          default::Sentence
      FILTER
          (((.score >= 0.8) AND (NOT (.message.author.is_bot) OR .message.author.is_webhook)) AND NOT ((.message.container IN {316066233755631616, 786041291707777034, 914305039764426772, 1128714905932021821})))
  );
  ALTER TYPE default::Author {
      ALTER LINK user_messages {
          USING (SELECT
              .<author[IS default::Message]
          FILTER
              ((NOT (.author.is_bot) OR .author.is_webhook) AND NOT ((.container IN {316066233755631616, 786041291707777034, 914305039764426772, 1128714905932021821})))
          );
      };
  };
  ALTER TYPE default::Community {
      ALTER LINK user_messages {
          USING (SELECT
              .<community[IS default::Message]
          FILTER
              ((NOT (.author.is_bot) OR .author.is_webhook) AND NOT ((.container IN {316066233755631616, 786041291707777034, 914305039764426772, 1128714905932021821})))
          );
      };
  };
};

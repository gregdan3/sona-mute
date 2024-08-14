CREATE MIGRATION m1ksqok4tl4qlys2ea7uebupely2yenn3kzq3tsjy6djobdxgm2mtq
    ONTO m1hbjnyiji77ekglvwekngngksa65osmnfwgv3lrpgrgzi2ueolmaa
{
  ALTER ALIAS default::NonTPUserSentence USING (SELECT
      default::Sentence
  FILTER
      (((.score < 0.8) AND (NOT (.message.author.is_bot) OR .message.author.is_webhook)) AND NOT ((.message.container IN {316066233755631616, 786041291707777034, 914305039764426772, 1128714905932021821, 1187212477155528804})))
  );
  ALTER ALIAS default::TPUserSentence USING (SELECT
      default::Sentence
  FILTER
      (((.score >= 0.8) AND (NOT (.message.author.is_bot) OR .message.author.is_webhook)) AND NOT ((.message.container IN {316066233755631616, 786041291707777034, 914305039764426772, 1128714905932021821, 1187212477155528804})))
  );
  ALTER TYPE default::Author {
      ALTER LINK user_messages {
          USING (SELECT
              .<author[IS default::Message]
          FILTER
              ((NOT (.author.is_bot) OR .author.is_webhook) AND NOT ((.container IN {316066233755631616, 786041291707777034, 914305039764426772, 1128714905932021821, 1187212477155528804})))
          );
      };
  };
  ALTER TYPE default::Community {
      ALTER LINK user_messages {
          USING (SELECT
              .<community[IS default::Message]
          FILTER
              ((NOT (.author.is_bot) OR .author.is_webhook) AND NOT ((.container IN {316066233755631616, 786041291707777034, 914305039764426772, 1128714905932021821, 1187212477155528804})))
          );
      };
  };
};

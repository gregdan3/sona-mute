CREATE MIGRATION m1it3mw7whxbmu7tqahupqckagfslhgnpyizgke6ncbrzvnkktbjoa
    ONTO m1yp32myzr2you5qnhucqqvr6f63zw3zfnqrc7tzacdi7pyzs3g32q
{
  ALTER TYPE default::Message {
      ALTER PROPERTY container {
          SET default := 0;
          SET REQUIRED USING (<std::int64>0);
      };
  };
  ALTER ALIAS default::NonTPUserSentence USING (SELECT
      default::Sentence
  FILTER
      (((.score < 0.8) AND (NOT (.message.author.is_bot) OR .message.author.is_webhook)) AND NOT ((.message.container IN {316066233755631616, 786041291707777034, 914305039764426772, 1128714905932021821})))
  );
  ALTER ALIAS default::TPUserSentence USING (SELECT
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

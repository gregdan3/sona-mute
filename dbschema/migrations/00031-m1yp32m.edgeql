CREATE MIGRATION m1yp32myzr2you5qnhucqqvr6f63zw3zfnqrc7tzacdi7pyzs3g32q
    ONTO m1y7fhtsfxj4wa46j744kfxnoelosod4p5bfffats4ae4c2y2jh4ya
{
  ALTER ALIAS default::NonTPUserSentence USING (SELECT
      default::Sentence
  FILTER
      (((.score < 0.8) AND (NOT (.message.author.is_bot) OR .message.author.is_webhook)) AND (NOT ((.message.container IN {316066233755631616, 786041291707777034, 914305039764426772, 1128714905932021821})) OR NOT (EXISTS (.message.container))))
  );
  ALTER ALIAS default::TPUserSentence USING (SELECT
      default::Sentence
  FILTER
      (((.score >= 0.8) AND (NOT (.message.author.is_bot) OR .message.author.is_webhook)) AND (NOT ((.message.container IN {316066233755631616, 786041291707777034, 914305039764426772, 1128714905932021821})) OR NOT (EXISTS (.message.container))))
  );
  ALTER TYPE default::Author {
      ALTER LINK user_messages {
          USING (SELECT
              .<author[IS default::Message]
          FILTER
              ((NOT (.author.is_bot) OR .author.is_webhook) AND (NOT ((.container IN {316066233755631616, 786041291707777034, 914305039764426772, 1128714905932021821})) OR NOT (EXISTS (.container))))
          );
      };
  };
  ALTER TYPE default::Community {
      ALTER LINK user_messages {
          USING (SELECT
              .<community[IS default::Message]
          FILTER
              ((NOT (.author.is_bot) OR .author.is_webhook) AND (NOT ((.container IN {316066233755631616, 786041291707777034, 914305039764426772, 1128714905932021821})) OR NOT (EXISTS (.container))))
          );
      };
  };
};

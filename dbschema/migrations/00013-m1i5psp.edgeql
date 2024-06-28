CREATE MIGRATION m1i5pspbuywkuobwx4ofymmgzuix7n7osl5encgsnophj3w3joxafa
    ONTO m1ilp7ram4fksuonae3jotsqaocvxwmivbmgdaye756rv5zjkxjfma
{
  ALTER ALIAS default::UserMessage USING (SELECT
      default::Message
  FILTER
      (((.author.is_bot AND .author.is_webhook) OR NOT (.author.is_bot)) AND NOT ((.container IN {316066233755631616, 786041291707777034, 914305039764426772, 1128714905932021821})))
  );
  ALTER TYPE default::Author {
      DROP INDEX ON ((.is_bot, .is_webhook));
      DROP INDEX ON (.is_bot);
      DROP INDEX ON (.is_webhook);
  };
  ALTER TYPE default::Message {
      DROP INDEX ON (.container);
      DROP INDEX ON (.postdate);
  };
  ALTER TYPE default::Sentence {
      DROP INDEX ON (.score);
  };
};

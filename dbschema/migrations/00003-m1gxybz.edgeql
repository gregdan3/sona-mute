CREATE MIGRATION m1gxybzbalkspnes57rdwjvu2d7ws6bwd43jpmrpu6t6iqgcuacova
    ONTO m15hhklk4cfgdapmdvxhez77ssjbs5uculkopa6d2uzikij7jfybca
{
  CREATE ALIAS default::RelevantMessages := (
      SELECT
          default::Message
      FILTER
          ((.author.is_bot = .author.is_webhook) AND NOT ((.container IN {316066233755631616, 786041291707777034, 914305039764426772, 1128714905932021821})))
  );
};

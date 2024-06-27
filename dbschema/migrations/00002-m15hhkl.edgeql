CREATE MIGRATION m15hhklk4cfgdapmdvxhez77ssjbs5uculkopa6d2uzikij7jfybca
    ONTO m1ha3y57pahg6hdzq2mogvl7bdlmshbi3f7bkqxtvyfyrlavhzof7q
{
  ALTER TYPE default::Author {
      CREATE REQUIRED PROPERTY is_bot: std::bool {
          SET REQUIRED USING (<std::bool>{false});
      };
      CREATE REQUIRED PROPERTY is_webhook: std::bool {
          SET REQUIRED USING (<std::bool>{false});
      };
  };
};

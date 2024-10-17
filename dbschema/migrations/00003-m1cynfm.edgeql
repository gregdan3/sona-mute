CREATE MIGRATION m1cynfmjcql5x3cdaj4vnqn6kxyfg2bovw5fdvpe7y4f226xlugxgq
    ONTO m1boop54cfqgcdxdgeebxjqgopm2skdhkce7ba34o3hwzpoitrnf5q
{
  ALTER TYPE default::Frequency {
      CREATE REQUIRED MULTI LINK authors: default::Author {
          SET REQUIRED USING (<default::Author>{});
      };
  };
  ALTER TYPE default::Frequency {
      ALTER PROPERTY occurrences {
          RENAME TO hits;
      };
  };
};

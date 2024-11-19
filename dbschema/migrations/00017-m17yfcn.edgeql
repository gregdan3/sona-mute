CREATE MIGRATION m17yfcned3hqhalelpzxesxqz2yx3ixjbbh5li4u4bj6bpf3r63uoa
    ONTO m1iry7d7kvelg63zcmuo7iknj4cuficmmft57i32p5jpjh57jhw2la
{
  ALTER TYPE default::Author {
      DROP LINK tp_sentences;
  };
  ALTER TYPE default::Author {
      CREATE PROPERTY num_tp_sentences: std::int64 {
          CREATE REWRITE
              INSERT 
              USING (SELECT
                  std::count(.<author[IS default::Message].tp_sentences)
              );
          CREATE REWRITE
              UPDATE 
              USING (SELECT
                  std::count(.<author[IS default::Message].tp_sentences)
              );
      };
  };
};

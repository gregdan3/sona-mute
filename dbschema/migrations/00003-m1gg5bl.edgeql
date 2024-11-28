CREATE MIGRATION m1gg5bloh3wjdtacdlzwgzfftc4njqcseddp2brrdxpdinei5d77fq
    ONTO m1tp4hwwja22rlryeyklsrygk5mqusmu6e6h6qoowvmepd6sidivia
{
  ALTER TYPE default::Term {
      CREATE PROPERTY total_hits: std::int64 {
          SET default := 0;
      };
  };
  ALTER TYPE default::Frequency {
      CREATE TRIGGER update_total_hits
          AFTER INSERT 
          FOR EACH 
              WHEN ((__new__.min_sent_len = 1))
          DO (UPDATE
              default::Term
          FILTER
              (.id = __new__.id)
          SET {
              total_hits := (.total_hits + __new__.hits)
          });
  };
  ALTER TYPE default::Term {
      CREATE INDEX ON ((.text, .len, .total_hits));
  };
  ALTER TYPE default::Term {
      DROP INDEX ON ((.text, .len));
  };
};

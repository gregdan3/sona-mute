CREATE MIGRATION m1gcvvant4hhcvnvruuq3lrg5ow5fcevezgw4ospnaj22o4gmbexqa
    ONTO m17yfcned3hqhalelpzxesxqz2yx3ixjbbh5li4u4bj6bpf3r63uoa
{
  ALTER TYPE default::Author {
      ALTER PROPERTY num_tp_sentences {
          SET REQUIRED USING (SELECT
              std::count(.<author[IS default::Message].tp_sentences)
          );
      };
  };
};

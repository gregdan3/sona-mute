CREATE MIGRATION m14qfafg4upg67tktn6p3ia3rh26sp2mtdvo7s3f37iknwnhlflp6a
    ONTO m1gcvvant4hhcvnvruuq3lrg5ow5fcevezgw4ospnaj22o4gmbexqa
{
  ALTER TYPE default::Author {
      ALTER PROPERTY num_tp_sentences {
          RESET OPTIONALITY;
      };
  };
};

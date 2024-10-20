CREATE MIGRATION m1v65jte4x5qjol6fnkypvvdrhoqljwrn4h7irg2xoee76rl2wtpba
    ONTO m1xuyxchpkcyuktxo76gpu3in2ecz7bczshcrhjlu76yokbzo3aooa
{
  ALTER TYPE default::Author {
      CREATE MULTI LINK tp_sentences := (SELECT
          .<author[IS default::Message].tp_sentences
      );
  };
};

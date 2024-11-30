CREATE MIGRATION m16sxholkea2643qnmxyyvuuqkzbclqguzhxnzyb57c434jptcy3tq
    ONTO m1gpk3b3thxdeajmwzvtlhx3awidtuk2mnkqvtwbz3zs4prctfe73a
{
  ALTER TYPE default::Author {
      ALTER PROPERTY num_tp_sentences {
          SET default := 0;
          DROP REWRITE
              INSERT ;
              DROP REWRITE
                  UPDATE ;
              };
          };
};

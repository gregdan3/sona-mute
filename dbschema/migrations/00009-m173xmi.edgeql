CREATE MIGRATION m173xmi3qtbz3aucde2vctaeg5fz6bzd6ejh6hdmzxhbg5zvpx3ola
    ONTO m16sxholkea2643qnmxyyvuuqkzbclqguzhxnzyb57c434jptcy3tq
{
  ALTER TYPE default::Term {
      CREATE INDEX ON (.total_hits);
  };
};

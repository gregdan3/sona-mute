CREATE MIGRATION m1jokknhcgspnzyorqholptkk3iua345s55jp5yxyeq3kxz2jwa7mq
    ONTO m1ze2ppg2wrqdi6klkmuyauatv5rzivalobhmo4wdrnja3iafsasma
{
  ALTER TYPE default::Message {
      CREATE INDEX ON (.container);
  };
  ALTER TYPE default::Sentence {
      CREATE INDEX ON (.score);
  };
};

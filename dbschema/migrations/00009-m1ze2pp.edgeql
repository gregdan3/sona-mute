CREATE MIGRATION m1ze2ppg2wrqdi6klkmuyauatv5rzivalobhmo4wdrnja3iafsasma
    ONTO m1dyouhrylngqp2crmtvfmmrrdwgglo6urnnzbssdu5er55q6mjfoq
{
  ALTER TYPE default::Message {
      CREATE INDEX ON (.postdate);
  };
};

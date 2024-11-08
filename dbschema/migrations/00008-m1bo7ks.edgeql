CREATE MIGRATION m1bo7ksosyif3566nbftsyf6zsthsbggmcyry57r6zinpb2z4iua7q
    ONTO m1nkonpbl5da63t7mobdckxaqwsqn4k54e3aqvoy6h3e7vfvow7paa
{
  ALTER TYPE default::Frequency {
      CREATE INDEX ON ((.min_sent_len, .day));
  };
  ALTER TYPE default::Frequency {
      DROP INDEX ON ((.term, .min_sent_len, .day));
  };
  ALTER TYPE default::Frequency {
      CREATE INDEX ON (.day);
  };
  ALTER TYPE default::Frequency {
      CREATE INDEX ON (.min_sent_len);
  };
};

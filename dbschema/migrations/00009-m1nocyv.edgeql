CREATE MIGRATION m1nocyvlal2tkv4uqxivgkdiiogiqxhbahqixv3tpcgi56pgkcz2lq
    ONTO m1bo7ksosyif3566nbftsyf6zsthsbggmcyry57r6zinpb2z4iua7q
{
  ALTER TYPE default::Frequency {
      CREATE INDEX ON (.term);
      CREATE INDEX ON ((.term, .min_sent_len, .day));
  };
};

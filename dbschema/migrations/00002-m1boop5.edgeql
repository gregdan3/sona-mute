CREATE MIGRATION m1boop54cfqgcdxdgeebxjqgopm2skdhkce7ba34o3hwzpoitrnf5q
    ONTO m1y7bkszq4r5c6vfqnt2gdxnfiol6gt7kt7bvvpwz6wjmu3ntyt5xq
{
  ALTER TYPE default::Frequency {
      DROP INDEX ON (.community);
  };
  ALTER TYPE default::Frequency {
      CREATE INDEX ON ((.phrase, .min_sent_len, .day));
  };
  ALTER TYPE default::Frequency {
      DROP INDEX ON (.phrase);
  };
  ALTER TYPE default::Frequency {
      DROP INDEX ON (.day);
  };
  ALTER TYPE default::Frequency {
      DROP INDEX ON (.min_sent_len);
  };
};

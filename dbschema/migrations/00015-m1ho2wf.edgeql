CREATE MIGRATION m1ho2wfr2ot4ybswrzhobwprqioy3auvphh7l32mnstwq24cxxeufa
    ONTO m15kuiowhqykocpjguo2cqonbnzm5jlxiatvpwngpwtl5rift3x3bq
{
  ALTER TYPE default::Frequency {
      DROP INDEX ON ((.min_sent_len, .day));
  };
  ALTER TYPE default::Frequency {
      DROP INDEX ON (.term);
  };
  ALTER TYPE default::Frequency {
      DROP INDEX ON ((.term, .min_sent_len, .day));
  };
  ALTER TYPE default::Frequency {
      CREATE INDEX ON ((.day, .min_sent_len, .term));
  };
  ALTER TYPE default::Frequency {
      DROP INDEX ON (.day);
  };
  ALTER TYPE default::Frequency {
      DROP INDEX ON (.min_sent_len);
  };
};

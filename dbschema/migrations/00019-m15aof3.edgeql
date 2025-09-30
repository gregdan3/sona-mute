CREATE MIGRATION m15aof3ai222vlvmwlml2xa3kkhayzdwnx55pvwyqqad7atsskbqwq
    ONTO m1wylesblami3i3b5wtb3zksl2qd63ycpo7zubh4jochcomcmytocq
{
  ALTER TYPE default::Frequency {
      DROP CONSTRAINT std::exclusive ON ((.term, .attr, .community, .min_sent_len, .day));
  };
  ALTER TYPE default::Frequency {
      CREATE CONSTRAINT std::exclusive ON ((.term, .attr, .community, .day));
  };
  ALTER TYPE default::Frequency {
      DROP INDEX ON ((.term, .min_sent_len, .day));
  };
  ALTER TYPE default::Frequency {
      DROP INDEX ON ((.day, .min_sent_len, .term));
  };
  ALTER TYPE default::Frequency {
      CREATE INDEX ON ((.term, .attr, .day));
      DROP PROPERTY min_sent_len;
  };
  ALTER SCALAR TYPE default::Attribute EXTENDING enum<All, `Start`, `End`, Full, Long>;
};

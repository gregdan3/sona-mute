CREATE MIGRATION m1wylesblami3i3b5wtb3zksl2qd63ycpo7zubh4jochcomcmytocq
    ONTO m1l2ahl42renvltuudrr6y63nmgnufbd6b3w6pjyg773jeswbnjj5q
{
  ALTER SCALAR TYPE default::FrequencyType RENAME TO default::Attribute;
  ALTER TYPE default::Frequency {
      DROP CONSTRAINT std::exclusive ON ((.term, .type, .community, .min_sent_len, .day));
  };
  ALTER TYPE default::Frequency {
      ALTER PROPERTY type {
          RENAME TO attr;
      };
  };
  ALTER TYPE default::Frequency {
      CREATE CONSTRAINT std::exclusive ON ((.term, .attr, .community, .min_sent_len, .day));
  };
  ALTER TYPE default::Sentence {
      ALTER PROPERTY len {
          SET TYPE std::int32;
      };
  };
};

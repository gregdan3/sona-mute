CREATE MIGRATION m14bmrqa2myybj5a3jh7n5lnrng356y33ndm7cgvxe5v2iei66e3ja
    ONTO m16gqvvzjn7ocx5m4kj7o2j6hdyimdbfndzy7v4xrlkllqucwkilsa
{
  ALTER TYPE default::Frequency {
      CREATE CONSTRAINT std::exclusive ON ((.text, .length, .community, .day, .is_word));
  };
  ALTER TYPE default::Frequency {
      DROP CONSTRAINT std::exclusive ON ((.text, .length, .day, .is_word));
  };
};

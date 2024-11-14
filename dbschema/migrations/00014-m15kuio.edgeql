CREATE MIGRATION m15kuiowhqykocpjguo2cqonbnzm5jlxiatvpwngpwtl5rift3x3bq
    ONTO m1qr4jyy5swx6nzs22buftsfrtkc6w74a34dwddyey2yhqaklwtt3q
{
  ALTER TYPE default::Author {
      DROP INDEX ON (.id);
  };
  ALTER TYPE default::Frequency {
      DROP INDEX ON (.hits);
  };
};

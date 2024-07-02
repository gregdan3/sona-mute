CREATE MIGRATION m1khwwpy46jntpb4qspfxszooxi6aq4utqg3in3m42umckmo5egdva
    ONTO m1zzhqzcf26cev46tmnekngkxwyym6o2q4yox2tw2vkpo3qvfnnyta
{
  CREATE TYPE default::Freq {
      CREATE REQUIRED PROPERTY day: std::datetime;
      CREATE REQUIRED PROPERTY is_word: std::bool;
      CREATE REQUIRED PROPERTY length: std::int64;
      CREATE REQUIRED PROPERTY text: std::str;
      CREATE CONSTRAINT std::exclusive ON ((.text, .length, .day, .is_word));
      CREATE REQUIRED PROPERTY occurrences: std::int64;
  };
};

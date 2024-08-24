CREATE MIGRATION m15yaslskfnljjofmazwbdyszao6xzak2i4nzyvvprngz2ewlljd3a
    ONTO m1t2j3yzqtjlnu3nc4kqwcocrn4vuvr2ufgxvqrehbghozfxojku5a
{
  CREATE TYPE default::Phrase {
      CREATE REQUIRED PROPERTY text: std::str;
      CREATE CONSTRAINT std::exclusive ON (.text);
      CREATE REQUIRED PROPERTY length: std::int16;
      CREATE INDEX ON ((.text, .length));
  };
  ALTER TYPE default::Frequency {
      CREATE REQUIRED LINK phrase: default::Phrase {
          SET REQUIRED USING (<default::Phrase>{});
      };
  };
  ALTER TYPE default::Frequency {
      CREATE CONSTRAINT std::exclusive ON ((.phrase, .community, .min_sent_len, .day));
  };
  ALTER TYPE default::Frequency {
      DROP CONSTRAINT std::exclusive ON ((.text, .min_sent_len, .community, .day));
  };
  ALTER TYPE default::Frequency {
      CREATE INDEX ON (.phrase);
  };
  ALTER TYPE default::Frequency {
      DROP INDEX ON (.phrase_len);
      DROP PROPERTY phrase_len;
      DROP PROPERTY text;
  };
};

CREATE MIGRATION m1zk5gmaou2guzc3ud7phmsvtwo74qaygydmbm7fnczgdpw5n6lgca
    ONTO m173xmi3qtbz3aucde2vctaeg5fz6bzd6ejh6hdmzxhbg5zvpx3ola
{
  ALTER TYPE default::Frequency {
      CREATE INDEX ON ((.term, .min_sent_len, .day));
  };
  ALTER TYPE default::Frequency {
      DROP INDEX ON (.day);
  };
  ALTER TYPE default::Term {
      DROP INDEX ON ((.text, .len, .total_hits));
      CREATE REQUIRED PROPERTY marked: std::bool {
          SET REQUIRED USING (<std::bool>{(((.text)[0] = '^') OR ((.text)[-1] = '$'))});
      };
  };
  ALTER TYPE default::Term {
      CREATE INDEX ON ((.total_hits, .len, .marked));
  };
  ALTER TYPE default::Term {
      DROP INDEX ON (.total_hits);
  };
  ALTER TYPE default::Term {
      CREATE INDEX ON (.text);
  };
  ALTER TYPE default::Term {
      CREATE INDEX ON ((.total_hits, .text, .len));
  };
};

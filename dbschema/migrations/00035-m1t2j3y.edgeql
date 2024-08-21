CREATE MIGRATION m1t2j3yzqtjlnu3nc4kqwcocrn4vuvr2ufgxvqrehbghozfxojku5a
    ONTO m1ksqok4tl4qlys2ea7uebupely2yenn3kzq3tsjy6djobdxgm2mtq
{
  ALTER TYPE default::Author {
      ALTER PROPERTY _id {
          SET TYPE std::bigint;
      };
  };
  ALTER TYPE default::Community {
      ALTER PROPERTY _id {
          SET TYPE std::bigint;
      };
  };
  ALTER TYPE default::Frequency {
      ALTER PROPERTY min_sent_len {
          SET TYPE std::int16;
      };
      ALTER PROPERTY phrase_len {
          SET TYPE std::int16;
      };
  };
  ALTER TYPE default::Message {
      ALTER PROPERTY _id {
          SET TYPE std::bigint;
      };
      ALTER PROPERTY container {
          RESET default;
          SET TYPE std::bigint;
      };
  };
  ALTER TYPE default::Platform {
      ALTER PROPERTY _id {
          SET TYPE std::int16;
      };
  };
};

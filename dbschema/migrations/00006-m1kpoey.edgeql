CREATE MIGRATION m1kpoey4a7xdaurl2i4bqb4pl3csjqy6afamayl3bu23r4myuv6evq
    ONTO m1jfm2lfcoiqcolulvsgyyjfx63xjux3las7perbgwuwk6szouah6q
{
  ALTER TYPE default::Term {
      CREATE INDEX ON (.len);
  };
};

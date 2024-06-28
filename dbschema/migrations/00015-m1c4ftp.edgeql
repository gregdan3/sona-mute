CREATE MIGRATION m1c4ftpwrzeqrqkulbb723q2xr7qvwgmh6gatpbkv6b2a7ua4jslca
    ONTO m1sfcv6syhdpkzblyt4afygqx7rj43agzxc4jsklslaf46paw6tmvq
{
  ALTER TYPE default::Sentence {
      CREATE INDEX ON (.score);
  };
};

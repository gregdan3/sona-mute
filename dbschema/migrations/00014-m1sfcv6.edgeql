CREATE MIGRATION m1sfcv6syhdpkzblyt4afygqx7rj43agzxc4jsklslaf46paw6tmvq
    ONTO m1i5pspbuywkuobwx4ofymmgzuix7n7osl5encgsnophj3w3joxafa
{
  ALTER TYPE default::Author {
      CREATE INDEX ON (.is_bot);
      CREATE INDEX ON (.is_webhook);
  };
  ALTER TYPE default::Message {
      CREATE INDEX ON (.container);
      CREATE INDEX ON (.postdate);
  };
};

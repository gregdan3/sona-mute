CREATE MIGRATION m1n56xctkytqn5u5lyheaevjkrgaez4zvhyhw5bxlaeek3acyr3iua
    ONTO m1jokknhcgspnzyorqholptkk3iua345s55jp5yxyeq3kxz2jwa7mq
{
  ALTER TYPE default::Author {
      CREATE INDEX ON (.is_bot);
      CREATE INDEX ON (.is_webhook);
  };
};

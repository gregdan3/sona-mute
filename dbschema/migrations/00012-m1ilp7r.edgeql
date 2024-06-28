CREATE MIGRATION m1ilp7ram4fksuonae3jotsqaocvxwmivbmgdaye756rv5zjkxjfma
    ONTO m1n56xctkytqn5u5lyheaevjkrgaez4zvhyhw5bxlaeek3acyr3iua
{
  ALTER TYPE default::Author {
      CREATE INDEX ON ((.is_bot, .is_webhook));
  };
};

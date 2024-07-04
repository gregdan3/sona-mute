CREATE MIGRATION m1gu4vnxuwoq4bzx72tzovpzd4mqbkljisy3luwykj2t6qnwmp5uqa
    ONTO m1tedzjfhadr4lwwkhb46ovap77vp7u4k5c5mbdpb2ii4kcwu6z5mq
{
  ALTER TYPE default::Frequency {
      CREATE INDEX ON (.community);
      CREATE INDEX ON (.is_word);
      CREATE INDEX ON (.length);
      CREATE INDEX ON (.day);
  };
};

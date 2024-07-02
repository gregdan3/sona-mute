CREATE MIGRATION m1tedzjfhadr4lwwkhb46ovap77vp7u4k5c5mbdpb2ii4kcwu6z5mq
    ONTO m14bmrqa2myybj5a3jh7n5lnrng356y33ndm7cgvxe5v2iei66e3ja
{
  CREATE ALIAS default::NonTPUserSentence := (
      SELECT
          default::Sentence
      FILTER
          (((.score < 0.8) AND (NOT (.message.author.is_bot) OR .message.author.is_webhook)) AND NOT ((.message.container IN {316066233755631616, 786041291707777034, 914305039764426772, 1128714905932021821})))
  );
};

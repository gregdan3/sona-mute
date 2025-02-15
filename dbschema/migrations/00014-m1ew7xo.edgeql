CREATE MIGRATION m1ew7xopn4z6yxhex63za7w5ak2bb6hkfgkdpjdvkmvk7bciqguh5q
    ONTO m1p2oascjhvenw4t3fiy34c5rxniov4qohn7bq5dcd3blohbv7dorq
{
  ALTER ALIAS default::TPUserSentence USING (SELECT
      default::Sentence
  FILTER
      (((.score >= 0.8) AND .message.is_counted) AND ((.len >= 4) OR (.message.score >= 0.3)))
  );
};

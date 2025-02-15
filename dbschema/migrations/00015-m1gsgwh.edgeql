CREATE MIGRATION m1gsgwhxokshsffmu2mvhb7juo52mrv7vthm3jjjta52jgyeqvoo3a
    ONTO m1ew7xopn4z6yxhex63za7w5ak2bb6hkfgkdpjdvkmvk7bciqguh5q
{
  ALTER ALIAS default::TPUserSentence USING (SELECT
      default::Sentence
  FILTER
      (((.score >= 0.8) AND .message.is_counted) AND ((.len >= 3) OR (.message.score >= 0.3)))
  );
};

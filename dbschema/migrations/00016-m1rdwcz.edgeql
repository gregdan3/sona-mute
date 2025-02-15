CREATE MIGRATION m1rdwczvcu4uj2zcejaeqwkskumzc6t3se7t4zflejvkzt6mhyeina
    ONTO m1gsgwhxokshsffmu2mvhb7juo52mrv7vthm3jjjta52jgyeqvoo3a
{
  ALTER ALIAS default::TPUserSentence USING (SELECT
      default::Sentence
  FILTER
      ((((.score >= 0.8) AND .message.is_counted) AND (.message.score > 0.1)) AND ((.len >= 3) OR (.message.score >= 0.3)))
  );
};

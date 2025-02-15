CREATE MIGRATION m1p2oascjhvenw4t3fiy34c5rxniov4qohn7bq5dcd3blohbv7dorq
    ONTO m1gzwoszzt6af2s5v7twmcmxe7te5iairligvhxmmcpdnapj5zgwoa
{
  ALTER ALIAS default::TPUserSentence USING (SELECT
      default::Sentence
  FILTER
      (((.score >= 0.8) AND .message.is_counted) AND ((.len > 2) OR (.message.score >= 0.265)))
  );
};

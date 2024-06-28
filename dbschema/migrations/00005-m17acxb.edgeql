CREATE MIGRATION m17acxbzc4qluwbfa7c7mwsq2xlsm7eqqcesrapuici3qlwubkj2ta
    ONTO m1ifksaqe7amtcirz6ss5mlsfnbgqe634h4ic4qyjkqy7lt3seai6q
{
  DROP ALIAS default::RelevantSentences;
  ALTER ALIAS default::RelevantMessages RENAME TO default::UserMessage;
  CREATE ALIAS default::TPSentence := (
      SELECT
          default::Sentence {
              words
          }
      FILTER
          ((.message IN default::UserMessage) AND (.score >= 0.8))
  );
};

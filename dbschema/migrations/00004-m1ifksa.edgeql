CREATE MIGRATION m1ifksaqe7amtcirz6ss5mlsfnbgqe634h4ic4qyjkqy7lt3seai6q
    ONTO m1gxybzbalkspnes57rdwjvu2d7ws6bwd43jpmrpu6t6iqgcuacova
{
  CREATE ALIAS default::RelevantSentences := (
      SELECT
          default::Sentence {
              words
          }
      FILTER
          ((.message IN default::RelevantMessages) AND (.score >= 0.8))
  );
};

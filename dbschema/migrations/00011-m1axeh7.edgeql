CREATE MIGRATION m1axeh7zqlwiozva35tqhyuivlwv7xhhcgtc2hi2wedgn2gycazika
    ONTO m1zk5gmaou2guzc3ud7phmsvtwo74qaygydmbm7fnczgdpw5n6lgca
{
  ALTER TYPE default::Message {
      CREATE REQUIRED PROPERTY score: std::float64 {
          SET REQUIRED USING (<std::float64>{1.0});
      };
  };
};

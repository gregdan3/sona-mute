CREATE MIGRATION m1gzwoszzt6af2s5v7twmcmxe7te5iairligvhxmmcpdnapj5zgwoa
    ONTO m1axeh7zqlwiozva35tqhyuivlwv7xhhcgtc2hi2wedgn2gycazika
{
  ALTER TYPE default::Sentence {
      CREATE REQUIRED PROPERTY len: std::int16 {
          SET REQUIRED USING (<std::int16>{std::len(.words)});
      };
  };
};

CREATE MIGRATION m1tp4hwwja22rlryeyklsrygk5mqusmu6e6h6qoowvmepd6sidivia
    ONTO m1ajmneitebkhvqbbqgxipk4mxhf7mkkjuduqte7wsmb6dnpibcvva
{
  ALTER TYPE default::Frequency {
      CREATE INDEX ON (.day);
  };
};

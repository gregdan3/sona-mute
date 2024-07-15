CREATE MIGRATION m1y7fhtsfxj4wa46j744kfxnoelosod4p5bfffats4ae4c2y2jh4ya
    ONTO m1i3zukt7y6pq7fupiffclzbsf3ujcj6jvqyk7phrplw332jfg7oba
{
  ALTER TYPE default::Author {
      ALTER PROPERTY name {
          RESET OPTIONALITY;
      };
  };
};

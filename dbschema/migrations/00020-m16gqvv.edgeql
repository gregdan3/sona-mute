CREATE MIGRATION m16gqvvzjn7ocx5m4kj7o2j6hdyimdbfndzy7v4xrlkllqucwkilsa
    ONTO m1gr7ytkqzlhvxza5hzs6u6pdvbxvjrd2lksg7i6ecopzeiwgc6xra
{
  ALTER TYPE default::Frequency {
      CREATE REQUIRED LINK community: default::Community {
          SET REQUIRED USING (<default::Community>{});
      };
  };
};

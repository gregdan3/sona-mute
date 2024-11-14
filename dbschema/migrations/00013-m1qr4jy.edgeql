CREATE MIGRATION m1qr4jyy5swx6nzs22buftsfrtkc6w74a34dwddyey2yhqaklwtt3q
    ONTO m1yms6ii3wg4x5bvreqaxf27uhmiaajoogjzwtqxxye2cyyps5wfhq
{
  ALTER TYPE default::Author {
      CREATE INDEX ON (.id);
  };
};

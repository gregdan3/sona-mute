CREATE MIGRATION m1yms6ii3wg4x5bvreqaxf27uhmiaajoogjzwtqxxye2cyyps5wfhq
    ONTO m1xjxgvrd4u27p5qxeu3k63c7ucrg34qyiqwfais37bwhi6xr2344a
{
  ALTER TYPE default::Frequency {
      CREATE INDEX ON (.hits);
  };
};

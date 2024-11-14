CREATE MIGRATION m166626bjui45n6sgmuykhnbwyxk25chggvpsy6h27agilb44ug6sq
    ONTO m1nocyvlal2tkv4uqxivgkdiiogiqxhbahqixv3tpcgi56pgkcz2lq
{
  ALTER TYPE default::Message {
      CREATE INDEX ON (.postdate);
  };
};

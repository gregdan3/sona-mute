CREATE MIGRATION m1xjxgvrd4u27p5qxeu3k63c7ucrg34qyiqwfais37bwhi6xr2344a
    ONTO m166626bjui45n6sgmuykhnbwyxk25chggvpsy6h27agilb44ug6sq
{
  ALTER TYPE default::Message {
      DROP INDEX ON (.postdate);
  };
  ALTER TYPE default::Term {
      CREATE INDEX ON (.text);
  };
  ALTER TYPE default::Term {
      DROP INDEX ON ((.text, .len));
  };
};

CREATE MIGRATION m16xolbmzu7pdgomqkromgridpsnois6gzxsxcthedciha2ew3gn3a
    ONTO m1v65jte4x5qjol6fnkypvvdrhoqljwrn4h7irg2xoee76rl2wtpba
{
  ALTER TYPE default::Term {
      DROP INDEX ON ((.text, .len));
  };
  ALTER TYPE default::Term {
      ALTER PROPERTY len {
          RENAME TO length;
      };
  };
  ALTER TYPE default::Term {
      CREATE INDEX ON ((.text, .length));
  };
};

CREATE MIGRATION m1eahdtyulb2jbmarsx3tbxrjzavhp2qjcuugas6nzjg5j63kbkaha
    ONTO m16xolbmzu7pdgomqkromgridpsnois6gzxsxcthedciha2ew3gn3a
{
  ALTER TYPE default::Term {
      DROP INDEX ON ((.text, .length));
  };
  ALTER TYPE default::Term {
      ALTER PROPERTY length {
          RENAME TO len;
      };
  };
  ALTER TYPE default::Term {
      CREATE INDEX ON ((.text, .len));
  };
};

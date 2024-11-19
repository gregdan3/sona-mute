CREATE MIGRATION m1iry7d7kvelg63zcmuo7iknj4cuficmmft57i32p5jpjh57jhw2la
    ONTO m1ho2wfr2ot4ybswrzhobwprqioy3auvphh7l32mnstwq24cxxeufa
{
  ALTER TYPE default::Term {
      DROP INDEX ON (.len);
  };
  ALTER TYPE default::Term {
      DROP INDEX ON (.text);
  };
  ALTER TYPE default::Term {
      CREATE INDEX ON ((.text, .len));
  };
};

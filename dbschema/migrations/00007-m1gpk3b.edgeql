CREATE MIGRATION m1gpk3b3thxdeajmwzvtlhx3awidtuk2mnkqvtwbz3zs4prctfe73a
    ONTO m1dnlf6igqtnnomvmxedqxj22xxruiwtdgavwsofgzwit7tf76vwua
{
  ALTER TYPE default::Frequency {
      DROP TRIGGER update_total_hits;
  };
};

CREATE MIGRATION m1dnlf6igqtnnomvmxedqxj22xxruiwtdgavwsofgzwit7tf76vwua
    ONTO m1oobv5grpv4kfu6tluyfvje46rd6rf53x52cnsc76jmks52f62huq
{
  ALTER TYPE default::Frequency {
      ALTER TRIGGER update_total_hits WHEN ((__new__.min_sent_len = __new__.term.len));
  };
};

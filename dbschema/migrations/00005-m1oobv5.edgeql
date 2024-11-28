CREATE MIGRATION m1oobv5grpv4kfu6tluyfvje46rd6rf53x52cnsc76jmks52f62huq
    ONTO m1abl3adc7o2pyuaqpuagpmqgm6dvhc5gwx7zwaqkeb54dxsx77aka
{
  ALTER TYPE default::Frequency {
      ALTER TRIGGER update_total_hits {
          WHEN ((__new__.min_sent_len = 1));
          USING (UPDATE
              default::Term
          FILTER
              (.id = __new__.term.id)
          SET {
              total_hits := (.total_hits + __new__.hits)
          });
      };
  };
};

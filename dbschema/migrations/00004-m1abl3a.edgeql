CREATE MIGRATION m1abl3adc7o2pyuaqpuagpmqgm6dvhc5gwx7zwaqkeb54dxsx77aka
    ONTO m1gg5bloh3wjdtacdlzwgzfftc4njqcseddp2brrdxpdinei5d77fq
{
  ALTER TYPE default::Frequency {
      ALTER TRIGGER update_total_hits RESET WHEN;
  };
};

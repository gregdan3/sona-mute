CREATE MIGRATION m173p2fq32wdquobwlcazthcx6xmnyf5lm4w6m7f4mo6ck4xfcpneq
    ONTO m15aof3ai222vlvmwlml2xa3kkhayzdwnx55pvwyqqad7atsskbqwq
{
  ALTER SCALAR TYPE default::Attribute EXTENDING enum<All, `Start`, `End`, Full, Long, Short, Inner>;
};

CREATE MIGRATION m1eueuv6wloti7birea3dw4zevrgvsijc43xqs3cx5sv422y5kyxpa
    ONTO m12gvncow7emv6w5zkyrzn3vrxmqp4bp5osrjjssyvpmf23lgejimq
{
  ALTER TYPE default::Message {
      DROP INDEX ON (.container);
  };
  ALTER TYPE default::Message {
      DROP INDEX ON (.postdate);
  };
  ALTER TYPE default::Message {
      CREATE INDEX ON ((.is_counted, .postdate));
  };
};

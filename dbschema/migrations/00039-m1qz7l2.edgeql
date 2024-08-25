CREATE MIGRATION m1qz7l2rd4x2fyjftixiuamomocmda7l4hulf7obbdriqxojgc7uha
    ONTO m1eueuv6wloti7birea3dw4zevrgvsijc43xqs3cx5sv422y5kyxpa
{
  ALTER TYPE default::Community {
      ALTER PROPERTY name {
          RESET OPTIONALITY;
      };
  };
};

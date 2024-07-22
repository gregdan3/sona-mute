CREATE MIGRATION m1hbjnyiji77ekglvwekngngksa65osmnfwgv3lrpgrgzi2ueolmaa
    ONTO m1it3mw7whxbmu7tqahupqckagfslhgnpyizgke6ncbrzvnkktbjoa
{
  ALTER TYPE default::Author {
      DROP CONSTRAINT std::exclusive ON ((._id, .platform));
  };
  ALTER TYPE default::Author {
      CREATE CONSTRAINT std::exclusive ON ((._id, .name, .platform));
  };
};

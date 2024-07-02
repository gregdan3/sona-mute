CREATE MIGRATION m1gr7ytkqzlhvxza5hzs6u6pdvbxvjrd2lksg7i6ecopzeiwgc6xra
    ONTO m1khwwpy46jntpb4qspfxszooxi6aq4utqg3in3m42umckmo5egdva
{
  ALTER TYPE default::Freq RENAME TO default::Frequency;
};

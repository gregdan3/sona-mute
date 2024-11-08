CREATE MIGRATION m1jfm2lfcoiqcolulvsgyyjfx63xjux3las7perbgwuwk6szouah6q
    ONTO m1eahdtyulb2jbmarsx3tbxrjzavhp2qjcuugas6nzjg5j63kbkaha
{
  ALTER TYPE default::Author {
      ALTER LINK platform {
          SET readonly := true;
      };
      ALTER PROPERTY _id {
          SET readonly := true;
      };
  };
  ALTER TYPE default::Community {
      ALTER LINK platform {
          SET readonly := true;
      };
      ALTER PROPERTY _id {
          SET readonly := true;
      };
  };
  ALTER TYPE default::Frequency {
      ALTER LINK community {
          SET readonly := true;
      };
      ALTER LINK term {
          SET readonly := true;
      };
      ALTER PROPERTY day {
          SET readonly := true;
      };
      ALTER PROPERTY min_sent_len {
          SET readonly := true;
      };
  };
  ALTER TYPE default::Sentence {
      ALTER LINK message {
          SET readonly := true;
      };
      ALTER PROPERTY words {
          SET readonly := true;
      };
  };
  ALTER TYPE default::Platform {
      ALTER PROPERTY _id {
          SET readonly := true;
      };
      ALTER PROPERTY name {
          SET readonly := true;
      };
  };
  ALTER TYPE default::Term {
      ALTER PROPERTY len {
          SET readonly := true;
      };
      ALTER PROPERTY text {
          SET readonly := true;
      };
  };
};

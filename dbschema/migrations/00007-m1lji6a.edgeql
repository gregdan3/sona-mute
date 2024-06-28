CREATE MIGRATION m1lji6ax23jfkibtdwfgdpwh4bmgr4m2zyotuhwvk6c27jjs66odoq
    ONTO m1y5e5kcoiwmvyefwvtiu6wb5ivdeubxkunqjuotwc2dsa6rvqug2a
{
  ALTER TYPE default::Community {
      CREATE MULTI LINK messages := (.<community[IS default::Message]);
      CREATE MULTI LINK user_messages := (SELECT
          .<community[IS default::Message]
      FILTER
          ((.author.is_bot = .author.is_webhook) AND NOT ((.container IN {316066233755631616, 786041291707777034, 914305039764426772, 1128714905932021821})))
      );
  };
};

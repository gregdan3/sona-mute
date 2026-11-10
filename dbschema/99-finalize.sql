CREATE ROLE api LOGIN PASSWORD 'samplepassword';
GRANT CONNECT ON DATABASE sonamute TO api;
GRANT USAGE ON SCHEMA public TO api;
GRANT SELECT ON  
  monthly,
  yearly,
  alltime,
  total_monthly,
  total_yearly,
  total_alltime 
TO api;

CREATE ROLE metabase LOGIN PASSWORD 'samplepassword';
GRANT CONNECT ON DATABASE sonamute TO metabase;
GRANT USAGE ON SCHEMA public TO metabase;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO metabase;

ALTER DEFAULT PRIVILEGES FOR ROLE metabase 
IN SCHEMA public
GRANT SELECT ON TABLES TO metabase;

CREATE DATABASE metabase OWNER metabase;

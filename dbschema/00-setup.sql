ALTER DATABASE sonamute SET work_mem = '128MB';
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

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

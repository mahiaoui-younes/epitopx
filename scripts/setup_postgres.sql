-- Setup EpitopX database and user
DO
$$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'epitopx') THEN
    CREATE ROLE epitopx LOGIN PASSWORD 'epitopx2024';
  END IF;
END
$$;

SELECT 'User epitopx ready' AS status;

DO
$$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'epitopx_db') THEN
    PERFORM dblink_exec('dbname=postgres', 'CREATE DATABASE epitopx_db OWNER epitopx');
  END IF;
END
$$;

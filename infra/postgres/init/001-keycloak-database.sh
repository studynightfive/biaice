#!/bin/sh
set -eu

test -n "${KEYCLOAK_DB:?KEYCLOAK_DB is required}"
test -n "${KEYCLOAK_DB_USER:?KEYCLOAK_DB_USER is required}"
test -n "${KEYCLOAK_DB_PASSWORD:?KEYCLOAK_DB_PASSWORD is required}"
test -n "${POSTGRES_DB:?POSTGRES_DB is required}"
test -n "${POSTGRES_MIGRATION_USER:?POSTGRES_MIGRATION_USER is required}"
test -n "${POSTGRES_MIGRATION_PASSWORD:?POSTGRES_MIGRATION_PASSWORD is required}"
test -n "${POSTGRES_RUNTIME_USER:?POSTGRES_RUNTIME_USER is required}"
test -n "${POSTGRES_RUNTIME_PASSWORD:?POSTGRES_RUNTIME_PASSWORD is required}"

psql --set ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname postgres \
  --set=kc_db="$KEYCLOAK_DB" \
  --set=kc_user="$KEYCLOAK_DB_USER" \
  --set=kc_password="$KEYCLOAK_DB_PASSWORD" \
  --set=app_db="$POSTGRES_DB" \
  --set=migration_user="$POSTGRES_MIGRATION_USER" \
  --set=migration_password="$POSTGRES_MIGRATION_PASSWORD" \
  --set=runtime_user="$POSTGRES_RUNTIME_USER" \
  --set=runtime_password="$POSTGRES_RUNTIME_PASSWORD" <<'EOSQL'
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'kc_user', :'kc_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'kc_user') \gexec

SELECT format(
  'CREATE ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS',
  :'migration_user', :'migration_password'
)
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'migration_user') \gexec

SELECT format(
  'CREATE ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS',
  :'runtime_user', :'runtime_password'
)
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'runtime_user') \gexec

SELECT format('CREATE DATABASE %I OWNER %I', :'kc_db', :'kc_user')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'kc_db') \gexec

SELECT format('REVOKE CONNECT ON DATABASE %I FROM PUBLIC', :'kc_db') \gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', :'kc_db', :'kc_user') \gexec
SELECT format('REVOKE CONNECT ON DATABASE %I FROM PUBLIC', :'app_db') \gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', :'app_db', :'migration_user') \gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', :'app_db', :'runtime_user') \gexec
EOSQL

psql --set ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --set=migration_user="$POSTGRES_MIGRATION_USER" \
  --set=runtime_user="$POSTGRES_RUNTIME_USER" <<'EOSQL'
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
SELECT format('GRANT USAGE, CREATE ON SCHEMA public TO %I', :'migration_user') \gexec
SELECT format('GRANT USAGE ON SCHEMA public TO %I', :'runtime_user') \gexec
SELECT format(
  'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO %I',
  :'migration_user', :'runtime_user'
) \gexec
SELECT format(
  'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO %I',
  :'migration_user', :'runtime_user'
) \gexec
EOSQL

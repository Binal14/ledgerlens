-- LedgerLens: read-only database role for the analytics layer.
-- Run as the Odoo DB owner (superuser "odoo"). Safe to re-run.
-- Password comes from a psql variable so it never lands in git:
--   psql ... -v ro_password="$LL_RO_PASSWORD" -f sql/roles.sql

\set ON_ERROR_STOP on

-- 1. Create the role once
SELECT NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ledgerlens_ro') AS need_role \gset
\if :need_role
CREATE ROLE ledgerlens_ro LOGIN;
\endif
ALTER ROLE ledgerlens_ro WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
    CONNECTION LIMIT 5 PASSWORD :'ro_password';

-- 2. Start from zero privileges (makes re-runs deterministic)
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM ledgerlens_ro;
REVOKE CREATE ON SCHEMA public FROM ledgerlens_ro;
GRANT CONNECT ON DATABASE ledgerlens TO ledgerlens_ro;
GRANT USAGE ON SCHEMA public TO ledgerlens_ro;

-- 3. Accounting tables: full read
GRANT SELECT ON account_move, account_move_line, account_account, account_journal
    TO ledgerlens_ro;

-- 4. Tables with personal data: only the columns LedgerLens needs (no email, phone, address)
GRANT SELECT (id, name, company_id, country_id, customer_rank, supplier_rank, active)
    ON res_partner TO ledgerlens_ro;
GRANT SELECT (id, name, currency_id) ON res_company TO ledgerlens_ro;

-- 5. Defence in depth (the GRANTs above are the real guard; these limit damage and abuse)
ALTER ROLE ledgerlens_ro SET default_transaction_read_only = on;
ALTER ROLE ledgerlens_ro SET statement_timeout = '5s';
ALTER ROLE ledgerlens_ro SET idle_in_transaction_session_timeout = '30s';

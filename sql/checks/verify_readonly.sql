-- LedgerLens: prove the read-only role is locked down.
-- Run AS ledgerlens_ro. Errors are EXPECTED for tests 2-7.
\set ON_ERROR_STOP off
\echo '--- 1. EXPECT OK: read posted move lines'
SELECT count(*) AS move_lines FROM account_move_line WHERE parent_state = 'posted';

\echo '--- 2. EXPECT permission denied: table not granted (users/passwords)'
SELECT count(*) FROM res_users;

\echo '--- 3. EXPECT permission denied: personal-data column not granted'
SELECT email FROM res_partner LIMIT 1;

\echo '--- 4. EXPECT error: write attempt'
UPDATE account_move SET ref = 'hacked' WHERE id = (SELECT min(id) FROM account_move);

\echo '--- 5. EXPECT permission denied: even after switching read-only off, GRANTs still block writes'
BEGIN;
SET TRANSACTION READ WRITE;
UPDATE account_move SET ref = 'hacked' WHERE id = (SELECT min(id) FROM account_move);
ROLLBACK;

\echo '--- 6. EXPECT error: create objects (blocked)'
CREATE TABLE pwned (id int);

\echo '--- 7. EXPECT statement timeout after 5s'
SELECT pg_sleep(6);

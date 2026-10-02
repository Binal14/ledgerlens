-- Minimal Odoo 17-shaped tables for offline tests (only the columns LedgerLens reads).
-- Data in *.csv is a snapshot of the synthetic seed database (no real data).
CREATE TABLE res_partner (id int PRIMARY KEY, name text, customer_rank int, supplier_rank int);
CREATE TABLE account_account (id int PRIMARY KEY, code text, name text, account_type text, reconcile boolean);
CREATE TABLE account_journal (id int PRIMARY KEY, name text, type text, code text, default_account_id int);
CREATE TABLE account_move (
    id int PRIMARY KEY, name text, move_type text, state text, date date, invoice_date date,
    invoice_date_due date, partner_id int, company_id int, journal_id int,
    amount_total numeric, amount_untaxed numeric, amount_residual numeric,
    amount_total_signed numeric, amount_residual_signed numeric, payment_state text,
    reversed_entry_id int);
CREATE TABLE account_move_line (
    id int PRIMARY KEY, move_id int, account_id int, journal_id int, partner_id int, company_id int,
    date date, date_maturity date, debit numeric, credit numeric, balance numeric,
    amount_residual numeric, reconciled boolean, parent_state text, display_type text);

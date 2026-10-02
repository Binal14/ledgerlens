# Week 1–2 notes

## Setup
- Odoo 17 Community + Postgres 15 in Docker; database `ledgerlens`, Invoicing app, German chart SKR03.
- Seed (`scripts/seed_data.py`, seed 42, data to 2026-09-30): 20 customers, 10 vendors, 150 invoices,
  80 bills, partial payments, 5 credit notes, 6 draft invoices (5,000 EUR each, must be excluded).
- 1,108 posted move lines.

## Read-only role (`sql/roles.sql`) — verified
| Test | Result |
|---|---|
| Read posted move lines | OK (1,108) |
| Read `res_users` | permission denied |
| Read partner e-mail | permission denied (column-level grant) |
| UPDATE invoice | blocked (read-only transaction) |
| Switch read-only off, then UPDATE | permission denied — GRANTs are the real guard |
| CREATE TABLE | blocked |
| 6 s query | cancelled by 5 s statement timeout |

## Revenue Q3 2026 (first hand-written query)
- SQL on journal lines: **611,953.30**
- Odoo Journal Items (same filters): 611,953.30
- Odoo Invoice Analysis: invoices 613,093.30 − credit notes 1,140.00 = **611,953.30** (independent source)
- Credit notes show up as the 1,140.00 *debit* on income accounts — summing `balance` nets them automatically.

## Semantic layer
10 metrics in `sql/metrics/`, all matching Odoo reference values to the cent (`tests/expected.json`).

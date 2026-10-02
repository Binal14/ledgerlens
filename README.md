# LedgerLens

A secure AI finance copilot for Odoo Accounting. Finance users ask questions in plain English;
LedgerLens answers with correct numbers, cites the journal entries behind them, forecasts cash and
flags suspicious payments.

> Status: **week 2 of 10** — data layer done (Odoo 17, read-only access, semantic layer of 10 metrics,
> all verified against Odoo to the cent). Next: LangGraph agent + MCP server.

## Why the AI never writes SQL
LLMs write plausible SQL that is often *wrong* for accounting (drafts included, refunds not netted,
partial payments ignored) and dangerous for security. LedgerLens exposes a **semantic layer**: reviewed,
tested SQL templates for each business metric. The agent only picks a metric and parameters; company
scope comes from the user's session, never from the prompt.

## Architecture (so far)
```
Odoo 17 + Postgres (Docker)
   └── read-only role `ledgerlens_ro` (SELECT on 4 accounting tables, column-level on partners,
       read-only transactions, 5 s timeout)
          └── semantic layer: app/semantic_layer + sql/metrics/*.sql
                 └── (next) LangGraph agent · MCP server · web UI
```

## Metrics
| Metric | Meaning |
|---|---|
| `revenue` | Income for a period, credit notes netted |
| `expenses` | Expenses booked in a period |
| `net_result` | Revenue − expenses |
| `receivables_open` | Owed by customers on a date |
| `payables_open` | Owed to vendors on a date |
| `overdue_invoices` | Open customer invoices past due |
| `ar_ageing` | Open receivables by days past due |
| `customer_payments` | Payments received, optionally per customer |
| `top_customers` | Customers ranked by revenue |
| `cash_position` | Bank/cash incl. unreconciled payments |

Definitions and edge cases: [docs/metrics.md](docs/metrics.md).

## Results
| Check | Result |
|---|---|
| Metrics matching Odoo's own reports (invoice analysis, residuals, payments) | **10 / 10, to the cent** |
| Ageing total reconciles with receivable account balance | ✅ |
| Read-only role: writes, DDL, `res_users`, partner e-mails blocked; 5 s timeout | ✅ 7 / 7 checks |
| Guardrail tests (unknown metric, bad params, SQL injection, company scope) | ✅ |
| Test suite | 25 tests, runs offline in CI on fixture data |

## Run it
```bash
cp .env.example .env            # set passwords
make up                         # Odoo on http://localhost:8069 (create DB "ledgerlens", install Invoicing)
make seed                       # synthetic company: invoices, bills, payments, credit notes, drafts
make roles && make verify-ro    # read-only role + proof it is locked down
pip install -e ".[dev]"
make test                       # offline tests on fixture data
make test-live                  # same tests against your live Odoo DB (read-only)
```

All data is synthetic (seed 42). Cost to run: €0.

# Metric definitions (Odoo 17)

All metrics: posted entries only (`parent_state = 'posted'` / `state = 'posted'`), filtered by the
caller's `company_ids`, amounts in company currency (`balance`, `*_signed` fields).

| Metric | Source | Logic | Edge cases |
|---|---|---|---|
| revenue | move lines | −Σ balance on `income`, `income_other` accounts by accounting date | Credit notes debit income → netted automatically. Drafts excluded. |
| expenses | move lines | Σ balance on `expense*` accounts | Vendor refunds netted. |
| net_result | move lines | −Σ balance on income + expense accounts | |
| receivables_open | move lines | Σ balance on `asset_receivable` up to `as_of` | Historically correct (payments credit AR on payment date). Unused credit notes reduce it. |
| payables_open | move lines | −Σ balance on `liability_payable` up to `as_of` | |
| overdue_invoices | invoices | `out_invoice` with residual > 0 and due ≤ as_of − min_days | Uses **current** residual. Partial payments show only the open part. |
| ar_ageing | invoices | residual of `out_invoice` + `out_refund` bucketed by days past due | Open credit notes are negative. Total must equal `receivables_open`. |
| customer_payments | move lines | −Σ balance on receivable lines in bank/cash journals | Optional `partner_id`. |
| top_customers | move lines | revenue grouped by partner | |
| cash_position | move lines | Σ balance in bank/cash journals on `asset_cash` + `asset_current` | Odoo 17 parks payments in *Outstanding Receipts/Payments* until bank reconciliation, so the bank account alone shows 0. |

## Lessons
- Summing invoice totals is wrong once refunds and partial payments exist; journal lines are the truth.
- `payment_state` alone is unreliable (`in_payment` vs `paid` depends on bank reconciliation); use residuals.
- A wrong `account_type` string fails silently (returns 0) — every metric has a test against Odoo.

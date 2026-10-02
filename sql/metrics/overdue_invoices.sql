-- overdue_invoices: open customer invoices past due by at least min_days_overdue on as_of.
-- Uses the CURRENT open amount (amount_residual_signed); as_of shifts the due-date cut-off.
SELECT am.id,
       am.name,
       rp.name                                  AS partner,
       am.invoice_date_due                      AS due_date,
       (%(as_of)s::date - am.invoice_date_due)  AS days_overdue,
       am.amount_residual_signed                AS amount_due
FROM account_move am
LEFT JOIN res_partner rp ON rp.id = am.partner_id
WHERE am.state = 'posted'
  AND am.move_type = 'out_invoice'
  AND am.company_id = ANY(%(company_ids)s)
  AND am.amount_residual_signed > 0
  AND am.invoice_date_due <= %(as_of)s::date - %(min_days_overdue)s::int
ORDER BY days_overdue DESC, am.id;

-- customer_payments: money received from customers in a period (optionally one partner).
-- Payment entries live in bank/cash journals and credit the receivable account.
SELECT COALESCE(-SUM(aml.balance), 0) AS value
FROM account_move_line aml
JOIN account_account aa ON aa.id = aml.account_id
JOIN account_journal aj ON aj.id = aml.journal_id
WHERE aml.parent_state = 'posted'
  AND aml.company_id = ANY(%(company_ids)s)
  AND aml.date BETWEEN %(date_from)s AND %(date_to)s
  AND aa.account_type = 'asset_receivable'
  AND aj.type IN ('bank', 'cash')
  AND (%(partner_id)s::int IS NULL OR aml.partner_id = %(partner_id)s::int);

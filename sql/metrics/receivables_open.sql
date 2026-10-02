-- receivables_open: what customers owe on a date = balance of receivable accounts up to that date.
-- Historically correct: payments credit the receivable account on their payment date.
-- Credit notes not yet used reduce the total (customer credit).
SELECT COALESCE(SUM(aml.balance), 0) AS value
FROM account_move_line aml
JOIN account_account aa ON aa.id = aml.account_id
WHERE aml.parent_state = 'posted'
  AND aml.company_id = ANY(%(company_ids)s)
  AND aml.date <= %(as_of)s
  AND aa.account_type = 'asset_receivable';

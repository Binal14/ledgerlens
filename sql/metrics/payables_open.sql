-- payables_open: what we owe vendors on a date = (credit) balance of payable accounts.
SELECT COALESCE(-SUM(aml.balance), 0) AS value
FROM account_move_line aml
JOIN account_account aa ON aa.id = aml.account_id
WHERE aml.parent_state = 'posted'
  AND aml.company_id = ANY(%(company_ids)s)
  AND aml.date <= %(as_of)s
  AND aa.account_type = 'liability_payable';

-- revenue: income for a period, credit notes netted automatically (they debit income accounts).
-- Source: posted journal lines on income accounts. Sign flipped: income is credit (negative balance).
SELECT COALESCE(-SUM(aml.balance), 0) AS value
FROM account_move_line aml
JOIN account_account aa ON aa.id = aml.account_id
WHERE aml.parent_state = 'posted'
  AND aml.company_id = ANY(%(company_ids)s)
  AND aml.date BETWEEN %(date_from)s AND %(date_to)s
  AND aa.account_type IN ('income', 'income_other');

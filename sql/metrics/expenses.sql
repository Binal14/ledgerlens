-- expenses: costs booked in a period (debit balance on expense accounts).
SELECT COALESCE(SUM(aml.balance), 0) AS value
FROM account_move_line aml
JOIN account_account aa ON aa.id = aml.account_id
WHERE aml.parent_state = 'posted'
  AND aml.company_id = ANY(%(company_ids)s)
  AND aml.date BETWEEN %(date_from)s AND %(date_to)s
  AND aa.account_type IN ('expense', 'expense_depreciation', 'expense_direct_cost');

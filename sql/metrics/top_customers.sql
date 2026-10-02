-- top_customers: revenue by customer for a period, highest first.
SELECT rp.id   AS partner_id,
       rp.name AS partner,
       -SUM(aml.balance) AS revenue
FROM account_move_line aml
JOIN account_account aa ON aa.id = aml.account_id
LEFT JOIN res_partner rp ON rp.id = aml.partner_id
WHERE aml.parent_state = 'posted'
  AND aml.company_id = ANY(%(company_ids)s)
  AND aml.date BETWEEN %(date_from)s AND %(date_to)s
  AND aa.account_type IN ('income', 'income_other')
GROUP BY rp.id, rp.name
ORDER BY revenue DESC
LIMIT %(limit)s;

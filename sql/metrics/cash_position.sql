-- cash_position: liquid funds on a date.
-- Odoo 17 posts payments to "Outstanding Receipts/Payments" (asset_current) until bank
-- statements are reconciled, so cash = bank/cash-journal lines on cash AND outstanding accounts.
SELECT COALESCE(SUM(aml.balance), 0) AS value
FROM account_move_line aml
JOIN account_account aa ON aa.id = aml.account_id
JOIN account_journal aj ON aj.id = aml.journal_id
WHERE aml.parent_state = 'posted'
  AND aml.company_id = ANY(%(company_ids)s)
  AND aml.date <= %(as_of)s
  AND aj.type IN ('bank', 'cash')
  AND aa.account_type IN ('asset_cash', 'asset_current');

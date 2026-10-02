-- ar_ageing: open receivables bucketed by days past due on as_of.
-- Includes open credit notes as negative amounts, like Odoo's aged receivable.
WITH open_items AS (
    SELECT am.amount_residual_signed AS amount,
           (%(as_of)s::date - am.invoice_date_due) AS days
    FROM account_move am
    WHERE am.state = 'posted'
      AND am.move_type IN ('out_invoice', 'out_refund')
      AND am.company_id = ANY(%(company_ids)s)
      AND am.amount_residual_signed <> 0
)
SELECT COALESCE(SUM(amount) FILTER (WHERE days <= 0), 0)              AS not_due,
       COALESCE(SUM(amount) FILTER (WHERE days BETWEEN 1 AND 30), 0)  AS d1_30,
       COALESCE(SUM(amount) FILTER (WHERE days BETWEEN 31 AND 60), 0) AS d31_60,
       COALESCE(SUM(amount) FILTER (WHERE days BETWEEN 61 AND 90), 0) AS d61_90,
       COALESCE(SUM(amount) FILTER (WHERE days > 90), 0)              AS d90_plus,
       COALESCE(SUM(amount), 0)                                       AS total
FROM open_items;

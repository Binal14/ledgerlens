select -sum(aml.balance) as revenue  from account_move_line aml  join account_account aa on aml.account_id = aa.id
 where aa.account_type in ('income','income_other') and
  aml.date  between '2026-07-01' and '2026-09-30' and
aml.parent_state = 'posted';



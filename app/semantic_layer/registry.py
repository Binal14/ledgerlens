"""
LedgerLens semantic layer.

The AI never writes SQL. It picks a metric name + parameters; this module validates
them, injects the caller's company scope, and runs a reviewed SQL template from
sql/metrics/ with bound parameters (no string formatting into SQL).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

SQL_DIR = Path(__file__).resolve().parents[2] / "sql" / "metrics"


# --- Parameter models (what the agent is allowed to pass) ----------------------
class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")  # unknown params are rejected


class Period(_Strict):
    date_from: date
    date_to: date

    @model_validator(mode="after")
    def _order(self):
        if self.date_from > self.date_to:
            raise ValueError("date_from must be on or before date_to")
        return self


class AsOf(_Strict):
    as_of: date


class OverdueParams(AsOf):
    min_days_overdue: int = Field(default=1, ge=1, le=3650)


class PaymentsParams(Period):
    partner_id: Optional[int] = Field(default=None, ge=1)


class TopParams(Period):
    limit: int = Field(default=5, ge=1, le=50)


@dataclass(frozen=True)
class Metric:
    name: str
    description: str
    params: type[BaseModel]
    shape: Literal["scalar", "row", "rows"]

    @property
    def sql(self) -> str:
        return (SQL_DIR / f"{self.name}.sql").read_text()


METRICS: dict[str, Metric] = {m.name: m for m in [
    Metric("revenue", "Income for a period, net of credit notes (EUR, excl. VAT).", Period, "scalar"),
    Metric("expenses", "Expenses booked in a period (EUR, excl. VAT).", Period, "scalar"),
    Metric("net_result", "Revenue minus expenses for a period.", Period, "scalar"),
    Metric("receivables_open", "Total owed by customers on a date.", AsOf, "scalar"),
    Metric("payables_open", "Total owed to vendors on a date.", AsOf, "scalar"),
    Metric("overdue_invoices", "Open customer invoices past due on a date.", OverdueParams, "rows"),
    Metric("ar_ageing", "Open receivables by days past due (not due, 1-30, 31-60, 61-90, 90+).", AsOf, "row"),
    Metric("customer_payments", "Payments received from customers in a period, optionally one customer.", PaymentsParams, "scalar"),
    Metric("top_customers", "Customers ranked by revenue for a period.", TopParams, "rows"),
    Metric("cash_position", "Bank and cash incl. payments not yet reconciled, on a date.", AsOf, "scalar"),
]}


class MetricError(ValueError):
    pass


def run_metric(conn, name: str, params: dict[str, Any], company_ids: list[int]) -> Any:
    """Validate and run one metric.

    company_ids comes from the authenticated session, never from the model/prompt.
    """
    metric = METRICS.get(name)
    if metric is None:
        raise MetricError(f"Unknown metric '{name}'. Allowed: {sorted(METRICS)}")
    if not company_ids or not all(isinstance(c, int) and c > 0 for c in company_ids):
        raise MetricError("company_ids must be a non-empty list of positive ints")

    bound = metric.params(**params).model_dump()
    bound["company_ids"] = list(company_ids)

    with conn.cursor() as cur:
        cur.execute(metric.sql, bound)
        cols = [c.name for c in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]

    if metric.shape == "scalar":
        return _num(rows[0]["value"])
    if metric.shape == "row":
        return {k: _num(v) for k, v in rows[0].items()}
    return [{k: _num(v) for k, v in r.items()} for r in rows]


def _num(v):
    return float(v) if isinstance(v, Decimal) else v

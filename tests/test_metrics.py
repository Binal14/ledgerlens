"""Every metric must reproduce Odoo's own numbers (tests/expected.json) to the cent."""
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.semantic_layer import METRICS, MetricError, run_metric

CENT = 0.005


def run(conn, name, exp, **params):
    return run_metric(conn, name, params, exp["company_ids"])


# --- Accuracy vs Odoo ---------------------------------------------------------
@pytest.mark.parametrize("period", ["q3", "ytd"])
def test_revenue(conn, expected, period):
    assert run(conn, "revenue", expected, **expected[period]) == pytest.approx(expected[f"revenue_{period}"], abs=CENT)


@pytest.mark.parametrize("period", ["q3", "ytd"])
def test_expenses(conn, expected, period):
    assert run(conn, "expenses", expected, **expected[period]) == pytest.approx(expected[f"expenses_{period}"], abs=CENT)


def test_net_result_is_revenue_minus_expenses(conn, expected):
    want = expected["revenue_q3"] - expected["expenses_q3"]
    assert run(conn, "net_result", expected, **expected["q3"]) == pytest.approx(want, abs=CENT)


def test_receivables_open(conn, expected):
    assert run(conn, "receivables_open", expected, as_of=expected["as_of"]) == pytest.approx(expected["receivables_open"], abs=CENT)


def test_payables_open(conn, expected):
    assert run(conn, "payables_open", expected, as_of=expected["as_of"]) == pytest.approx(expected["payables_open"], abs=CENT)


def test_ar_ageing_buckets_and_total(conn, expected):
    got = run(conn, "ar_ageing", expected, as_of=expected["as_of"])
    for bucket, want in expected["ar_ageing"].items():
        assert got[bucket] == pytest.approx(want, abs=CENT), bucket
    # ageing (invoice residuals) must reconcile with the receivable account balance
    assert got["total"] == pytest.approx(expected["receivables_open"], abs=CENT)


def test_overdue_invoices(conn, expected):
    rows = run(conn, "overdue_invoices", expected, as_of=expected["as_of"])
    assert len(rows) == expected["overdue_count"]
    assert all(r["days_overdue"] >= 1 and r["amount_due"] > 0 for r in rows)
    assert rows == sorted(rows, key=lambda r: (-r["days_overdue"], r["id"]))


def test_overdue_threshold_narrows(conn, expected):
    all_rows = run(conn, "overdue_invoices", expected, as_of=expected["as_of"])
    old = run(conn, "overdue_invoices", expected, as_of=expected["as_of"], min_days_overdue=60)
    assert 0 < len(old) < len(all_rows)
    assert all(r["days_overdue"] >= 60 for r in old)


def test_customer_payments(conn, expected):
    assert run(conn, "customer_payments", expected, **expected["q3"]) == pytest.approx(expected["customer_payments_q3"], abs=CENT)
    one = run(conn, "customer_payments", expected, date_from="2026-01-01", date_to="2026-12-31",
              partner_id=expected["customer_03_partner_id"])
    assert one == pytest.approx(expected["customer_03_payments_all"], abs=CENT)


def test_top_customers(conn, expected):
    rows = run(conn, "top_customers", expected, **expected["q3"], limit=5)
    assert [(r["partner"], round(r["revenue"], 2)) for r in rows] == [tuple(x) for x in expected["top5_q3"]]


def test_cash_position(conn, expected):
    assert run(conn, "cash_position", expected, as_of=expected["as_of"]) == pytest.approx(expected["cash_position"], abs=CENT)


# --- Edge cases the seed data was built for -----------------------------------
def test_drafts_are_excluded(conn, expected):
    """Six 5,000 EUR draft invoices exist; revenue must not include them."""
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM account_move WHERE state = 'draft' AND move_type = 'out_invoice'")
        assert cur.fetchone()[0] >= 1
    assert run(conn, "revenue", expected, **expected["q3"]) == pytest.approx(expected["revenue_q3"], abs=CENT)


def test_wrong_company_sees_nothing(conn, expected):
    assert run_metric(conn, "revenue", expected["q3"], [999]) == 0
    assert run_metric(conn, "overdue_invoices", {"as_of": expected["as_of"]}, [999]) == []


# --- Guardrails ---------------------------------------------------------------
def test_unknown_metric_rejected(conn, expected):
    with pytest.raises(MetricError):
        run(conn, "drop_tables", expected)


@pytest.mark.parametrize("params", [
    {"date_from": "2026-09-30", "date_to": "2026-07-01"},           # reversed period
    {"date_from": "2026-07-01", "date_to": "2026-09-30", "x": 1},   # unknown param
    {"date_from": "2026-07-01'; DROP TABLE account_move;--", "date_to": "2026-09-30"},  # injection
])
def test_bad_params_rejected(conn, expected, params):
    with pytest.raises(ValidationError):
        run_metric(conn, "revenue", params, expected["company_ids"])


@pytest.mark.parametrize("companies", [[], ["1"], [0], ["1 OR 1=1"]])
def test_company_scope_validated(conn, companies):
    with pytest.raises(MetricError):
        run_metric(conn, "revenue", {"date_from": "2026-07-01", "date_to": "2026-09-30"}, companies)


def test_metric_sql_is_read_only_and_parameterised():
    for m in METRICS.values():
        sql = re.sub(r"--[^\n]*", "", m.sql).upper()
        assert not re.search(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|GRANT|TRUNCATE|COPY)\b", sql), m.name
        assert "COMPANY_ID = ANY(%(COMPANY_IDS)S)" in sql, f"{m.name} lacks company scope"
        assert sql.count(";") == 1, f"{m.name} must be a single statement"


def test_every_metric_has_sql_file():
    names = {p.stem for p in (Path(__file__).resolve().parents[1] / "sql" / "metrics").glob("*.sql")}
    assert names == set(METRICS)

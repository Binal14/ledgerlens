"""
Two modes:
  * Fixture mode (default, used in CI): loads tests/fixtures/*.csv into a throwaway
    schema in LL_TEST_DSN (any Postgres you can write to).
  * Live mode: set LL_LIVE_DSN to your Odoo DB as the read-only role, e.g.
    postgresql://ledgerlens_ro:***@localhost:5432/ledgerlens
    The same tests then run against the real Odoo tables.
"""
import json
import os
import uuid
from pathlib import Path

import psycopg
import pytest

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"
TABLES = ["res_partner", "account_account", "account_journal", "account_move", "account_move_line"]


@pytest.fixture(scope="session")
def expected():
    return json.loads((HERE / "expected.json").read_text())


@pytest.fixture(scope="session")
def conn():
    live = os.getenv("LL_LIVE_DSN")
    if live:
        with psycopg.connect(live, autocommit=True) as c:
            yield c
        return

    dsn = os.getenv("LL_TEST_DSN", "postgresql://postgres:postgres@localhost:5432/postgres")
    schema = f"ll_test_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(dsn, autocommit=True) as c:
        c.execute(f'CREATE SCHEMA "{schema}"')
        c.execute(f'SET search_path TO "{schema}"')
        c.execute((FIX / "schema.sql").read_text())
        for t in TABLES:
            with open(FIX / f"{t}.csv") as f:
                header = f.readline().strip()
                with c.cursor().copy(f"COPY {t} ({header}) FROM STDIN WITH (FORMAT csv, NULL '')") as cp:
                    for line in f:
                        cp.write(line)
        try:
            yield c
        finally:
            c.execute(f'DROP SCHEMA "{schema}" CASCADE')

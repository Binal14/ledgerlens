"""
LedgerLens - seed Odoo 17 with reproducible accounting data.

Creates ~6 months of customer invoices, vendor bills, payments (full + partial),
credit notes and draft invoices, with deliberate edge cases for testing SQL metrics.

Usage:
    python scripts/seed_data.py            # uses defaults below or env vars
    ODOO_PASSWORD=admin python scripts/seed_data.py

Env vars: ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD
Run it on a FRESH database: it refuses to run twice (see marker check).
"""
import json
import os
import random
import sys
import xmlrpc.client
from datetime import date, timedelta
from pathlib import Path

URL = os.getenv("ODOO_URL", "http://localhost:8069")
DB = os.getenv("ODOO_DB", "ledgerlens")
USER = os.getenv("ODOO_USER", "admin")
PASSWORD = os.getenv("ODOO_PASSWORD", "admin")

SEED = 42
END = date(2026, 9, 30)            # fixed "today" -> identical data on every run
START = END - timedelta(days=182)  # ~6 months
N_CUSTOMERS, N_VENDORS = 20, 10
N_INVOICES, N_BILLS = 150, 80
N_CREDIT_NOTES, N_DRAFTS = 5, 6
MARKER = "LL Customer 01"

rng = random.Random(SEED)

# --- RPC helpers --------------------------------------------------------------
common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
uid = common.authenticate(DB, USER, PASSWORD, {})
if not uid:
    sys.exit(f"Login failed for {USER} on {DB} at {URL}")
models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object", allow_none=True)


def call(model, method, args, **kw):
    """execute_kw wrapper; tolerates Odoo methods that return None."""
    try:
        return models.execute_kw(DB, uid, PASSWORD, model, method, args, kw)
    except xmlrpc.client.Fault as e:
        if "cannot marshal None" in e.faultString:
            return None
        raise


def d(x: date) -> str:
    return x.isoformat()


def rand_date(a: date, b: date) -> date:
    return a + timedelta(days=rng.randint(0, (b - a).days))


# --- Guard: run once per database --------------------------------------------
if call("res.partner", "search_count", [[("name", "=", MARKER)]]):
    sys.exit("Seed data already exists. Recreate the database to reseed.")

company_id = call("res.users", "read", [[uid]], fields=["company_id"])[0]["company_id"][0]
bank = call("account.journal", "search",
            [[("type", "=", "bank"), ("company_id", "=", company_id)]], limit=1)
if not bank:
    sys.exit("No bank journal found. Is Invoicing/Accounting installed with a chart of accounts?")
bank_journal = bank[0]

# --- Master data ---------------------------------------------------------------
customers = [call("res.partner", "create", [{"name": f"LL Customer {i:02d}", "customer_rank": 1}])
             for i in range(1, N_CUSTOMERS + 1)]
vendors = [call("res.partner", "create", [{"name": f"LL Vendor {i:02d}", "supplier_rank": 1}])
           for i in range(1, N_VENDORS + 1)]

sale_products = [
    call("product.product", "create", [{"name": n, "type": "service", "list_price": p}])
    for n, p in [("Consulting hour", 95.0), ("Implementation package", 2400.0), ("Support plan", 450.0)]
]
purchase_products = [
    call("product.product", "create", [{"name": n, "type": "service", "standard_price": p,
                                         "purchase_ok": True, "sale_ok": False}])
    for n, p in [("Office rent", 1800.0), ("Software subscription", 120.0), ("Freelancer services", 650.0)]
]

# Weighted customers -> some clearly "top customers"
cust_weights = [rng.uniform(0.5, 1.0) * (3 if i < 3 else 1) for i in range(N_CUSTOMERS)]


def make_move(move_type, partner, inv_date, due_days, lines, post=True, ref=None):
    vals = {
        "move_type": move_type,
        "partner_id": partner,
        "invoice_date": d(inv_date),
        "invoice_date_due": d(inv_date + timedelta(days=due_days)),
        "invoice_line_ids": [(0, 0, l) for l in lines],
    }
    if ref:
        vals["ref"] = ref
    move_id = call("account.move", "create", [vals])
    if post:
        call("account.move", "action_post", [[move_id]])
    return move_id


def register_payment(move_id, pay_date, amount=None):
    ctx = {"active_model": "account.move", "active_ids": [move_id]}
    vals = {"payment_date": d(pay_date), "journal_id": bank_journal}
    if amount is not None:
        vals.update({"amount": round(amount, 2), "payment_difference_handling": "open"})
    wiz = call("account.payment.register", "create", [vals], context=ctx)
    call("account.payment.register", "action_create_payments", [[wiz]], context=ctx)


def amount_total(move_id):
    return call("account.move", "read", [[move_id]], fields=["amount_total"])[0]["amount_total"]


manifest = {"seed": SEED, "end_date": d(END), "invoices": [], "bills": [],
            "credit_notes": [], "drafts": [], "partial": [], "overdue_unpaid": []}

# --- Customer invoices ---------------------------------------------------------
for _ in range(N_INVOICES):
    partner = rng.choices(customers, weights=cust_weights)[0]
    inv_date = rand_date(START, END)
    due_days = rng.choice([14, 30, 30, 45])
    lines = [{"product_id": p, "quantity": rng.choice([1, 2, 4, 8, 10]),
              "price_unit": round(rng.uniform(0.8, 1.2) * base, 2)}
             for p, base in rng.sample(list(zip(sale_products, [95.0, 2400.0, 450.0])), k=rng.randint(1, 2))]
    inv = make_move("out_invoice", partner, inv_date, due_days, lines)
    manifest["invoices"].append(inv)

    due = inv_date + timedelta(days=due_days)
    old = due < END - timedelta(days=20)
    r = rng.random()
    pay_date = min(inv_date + timedelta(days=rng.randint(5, 50)), END)
    if r < (0.80 if old else 0.30):                       # fully paid
        register_payment(inv, pay_date)
    elif r < (0.90 if old else 0.40):                     # partial payment
        part = amount_total(inv) * rng.choice([0.25, 0.5, 0.6])
        register_payment(inv, pay_date, part)
        manifest["partial"].append(inv)
    elif due < END:                                       # left unpaid and overdue
        manifest["overdue_unpaid"].append(inv)

# --- Credit notes (partial refunds of posted invoices) ------------------------
for inv in rng.sample(manifest["invoices"], N_CREDIT_NOTES):
    src = call("account.move", "read", [[inv]], fields=["partner_id", "invoice_date"])[0]
    cn_date = min(date.fromisoformat(src["invoice_date"]) + timedelta(days=rng.randint(3, 20)), END)
    cn = make_move("out_refund", src["partner_id"][0], cn_date, 0,
                   [{"product_id": sale_products[0], "quantity": rng.randint(1, 5), "price_unit": 95.0}],
                   ref=f"Refund for move {inv}")
    manifest["credit_notes"].append(cn)

# --- Draft invoices (must be EXCLUDED by every metric) ------------------------
for _ in range(N_DRAFTS):
    dr = make_move("out_invoice", rng.choice(customers), rand_date(START, END), 30,
                   [{"product_id": sale_products[1], "quantity": 1, "price_unit": 5000.0}], post=False)
    manifest["drafts"].append(dr)

# --- Vendor bills -------------------------------------------------------------
for _ in range(N_BILLS):
    bill_date = rand_date(START, END)
    p, base = rng.choice(list(zip(purchase_products, [1800.0, 120.0, 650.0])))
    bill = make_move("in_invoice", rng.choice(vendors), bill_date, 30,
                     [{"product_id": p, "quantity": rng.randint(1, 3),
                       "price_unit": round(base * rng.uniform(0.9, 1.1), 2)}])
    manifest["bills"].append(bill)
    if rng.random() < 0.7:
        register_payment(bill, min(bill_date + timedelta(days=rng.randint(10, 35)), END))

# --- Save manifest (record IDs of edge cases, used later for tests/evals) -----
out = Path(__file__).resolve().parent / "seed_manifest.json"
out.write_text(json.dumps(manifest, indent=2))

print(f"Done. Seeded data up to {END}:")
for k in ["invoices", "bills", "credit_notes", "drafts", "partial", "overdue_unpaid"]:
    print(f"  {k:15s} {len(manifest[k])}")
print(f"Manifest written to {out}")

COMPOSE = docker compose -f infra/compose/docker-compose.yml
-include .env
export

.PHONY: up down logs seed roles verify-ro sql test test-live

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f odoo

# Seed Odoo with synthetic accounting data (fresh DB only)
seed:
	python scripts/seed_data.py

# Create/refresh the read-only role
roles:
	$(COMPOSE) exec -T db psql -U odoo -d ledgerlens -v ro_password="$(LL_RO_PASSWORD)" -f - < sql/roles.sql

# Prove the read-only role is locked down
verify-ro:
	$(COMPOSE) exec -T -e PGPASSWORD="$(LL_RO_PASSWORD)" db psql -h localhost -U ledgerlens_ro -d ledgerlens -f - < sql/checks/verify_readonly.sql

# Run any SQL file as the read-only role: make sql f=sql/metrics/revenue.sql
sql:
	$(COMPOSE) exec -T -e PGPASSWORD="$(LL_RO_PASSWORD)" db psql -h localhost -U ledgerlens_ro -d ledgerlens -f - < $(f)

# Offline tests on fixture data (needs any Postgres; LL_TEST_DSN in .env)
test:
	python -m pytest -q

# Same tests against your live Odoo DB as the read-only role
test-live:
	LL_LIVE_DSN="postgresql://ledgerlens_ro:$(LL_RO_PASSWORD)@localhost:5432/ledgerlens" python -m pytest -q

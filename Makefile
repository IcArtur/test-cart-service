COMPOSE := docker compose
SERVICE := web
RUN_SCRIPT := ./scripts/run.sh
TEST_SCRIPT := ./scripts/tests.sh

up:
	$(RUN_SCRIPT)

test:
	$(TEST_SCRIPT)

coverage:
	$(COMPOSE) run --rm $(SERVICE) python -m pytest --cov=orders --cov-report=term-missing

down:
	$(COMPOSE) down

build:
	$(COMPOSE) build

rebuild:
	$(COMPOSE) build --no-cache

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

restart:
	$(COMPOSE) restart

sh:
	$(COMPOSE) exec $(SERVICE) sh

bash:
	$(COMPOSE) exec $(SERVICE) bash

manage:
	$(COMPOSE) run --rm $(SERVICE) python manage.py $(ARGS)

makemigrations:
	$(COMPOSE) run --rm $(SERVICE) python manage.py makemigrations

migrate:
	$(COMPOSE) run --rm $(SERVICE) python manage.py migrate

load_fixtures:
	$(COMPOSE) run --rm $(SERVICE) python manage.py loaddata products

resetdb:
	$(COMPOSE) down -v
	$(COMPOSE) up -d db
	$(COMPOSE) run --rm $(SERVICE) python manage.py migrate

createsuperuser:
	$(COMPOSE) run --rm $(SERVICE) python manage.py createsuperuser

collectstatic:
	$(COMPOSE) run --rm $(SERVICE) python manage.py collectstatic --noinput

ruff-check:
	$(COMPOSE) run --rm $(SERVICE) ruff check .

ruff-fix:
	$(COMPOSE) run --rm $(SERVICE) ruff check . --fix

ruff-format:
	$(COMPOSE) run --rm $(SERVICE) ruff format .

lint: ruff-check

format: ruff-format

fmt: ruff-format

ci: ruff-format ruff-check migrate test

setup: migrate load_fixtures

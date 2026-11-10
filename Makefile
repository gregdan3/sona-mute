include .env
export
MAIN=docker compose

build:
	${MAIN} build postgres

up:
	${MAIN} up -d postgres

stop:
	${MAIN} stop postgres

down:
	${MAIN} down

destroy:
	${MAIN} down -v

logs:
	${MAIN} logs

dump:
	PGPASSWORD=$(POSTGRES_PASSWORD) ./dump-to-sqlite.sh "$(POSTGRES_HOST)" "$(POSTGRES_PORT)" "$(POSTGRES_USER)" "$(POSTGRES_DB)" "$$(date +%Y-%m-%d).sqlite"

psql:
	PGPASSWORD=$(POSTGRES_PASSWORD) psql --host $(POSTGRES_HOST) --port $(POSTGRES_PORT) --user $(POSTGRES_USER) --db $(POSTGRES_DB)

run:
	pdm run python ./src/sonamute/__main__.py

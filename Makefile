include .env
export
MAIN=docker compose

logs:
	${MAIN} logs

build:
	${MAIN} build

up:
	${MAIN} up -d

stop:
	${MAIN} stop

down:
	${MAIN} down

destroy:
	${MAIN} down -v

psql:
	PGPASSWORD=$(POSTGRES_PASSWORD) psql --host $(POSTGRES_HOST) --port $(POSTGRES_PORT) --user $(POSTGRES_USER) --db $(POSTGRES_DB)

run:
	pdm run python ./src/sonamute/__main__.py

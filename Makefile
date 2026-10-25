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

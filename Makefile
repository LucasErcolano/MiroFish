.PHONY: setup test smoke-test run-example docker-build docker-up

setup:
	npm run setup:all

test:
	npm test

smoke-test:
	npm run smoke-test

run-example:
	npm run run-example

docker-build:
	docker compose build

docker-up:
	docker compose up --build

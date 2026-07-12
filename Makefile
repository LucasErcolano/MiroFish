.PHONY: setup test smoke-test smoke-test-real run-example validate-outputs hygiene check docker-build docker-up docker-test docker-down

setup:
	npm run setup:all

test:
	npm test

smoke-test:
	npm run smoke-test

smoke-test-real:
	npm run smoke-test:real

run-example:
	npm run run-example

validate-outputs:
	npm run validate-outputs

hygiene:
	npm run hygiene

check:
	npm run check

docker-build:
	docker compose build

docker-up:
	npm run docker-up

docker-test:
	npm run docker-test

docker-down:
	npm run docker-down

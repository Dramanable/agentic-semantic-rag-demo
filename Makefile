# Everything runs in Docker: nothing to install on the host.
.PHONY: up down test eval logs reset

up:
	docker compose up --build

down:
	docker compose down

test:
	docker compose --profile test run --rm --build tests

# Measure retrieval quality and how trustworthy the confidence is (see eval/dataset.json).
eval:
	docker compose --profile eval run --rm --build eval

logs:
	docker compose logs -f api

# Delete documents and vector store (the data volume).
reset:
	docker compose down -v

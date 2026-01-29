.PHONY: install run dev migrate revision upgrade downgrade current test

install:
	pip install -r requirements.txt

run:
	uvicorn app.main:app --reload --port 9000

dev: run

migrate:
	python -m alembic revision --autogenerate -m "$(m)"

revision: migrate

upgrade:
	python -m alembic upgrade head

downgrade:
	python -m alembic downgrade -1

current:
	python -m alembic current

test:
	pytest -q

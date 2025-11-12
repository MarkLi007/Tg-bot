run:
	PYTHONPATH=src .venv/bin/python -m main

fmt:
	ruff format

lint:
	ruff check

test:
	pytest -q

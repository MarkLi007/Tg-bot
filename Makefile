run:
python -m src.main

fmt:
ruff format

lint:
ruff check

test:
pytest -q

#!/bin/bash
# 1  Create isolated env
# pyenv install 3.12.3  # once
# pyenv local 3.12.3
# python -m venv .venv && source .venv/bin/activate
# pip install -r requirements-dev.txt

# 2  Lint + type-check + static compile
ruff check legal_parser tests
mypy legal_parser  # optional but recommended
python -m compileall -q legal_parser  # catches syntax errors early

# 3  Run tests fast & loud
pytest -q -x --maxfail=1 --asyncio-mode=strict --timeout=20

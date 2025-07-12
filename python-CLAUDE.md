# Python Project Guidelines – python-CLAUDE.md

This document outlines language-specific standards, tools, and workflows for Python-based projects supported by the Claude CLI.

---

## Python Stack Overview

- **Language Version:** Python 3.12+
- **Frameworks:** Django, FastAPI, Flask (project-dependent)
- **Testing:** Pytest, Hypothesis
- **Linting:** Ruff, Black, isort
- **Typing:** mypy (strict)
- **Configuration:** Pydantic Settings v2
- **Environment Management:** `pyenv`, `venv`, `poetry`

---

## Python Code Standards

### Core Principles

1. Brutally simple code: Functions under 15 lines.
2. Single-responsibility classes; avoid God-objects.
3. Prefer functional-core, imperative-shell.
4. Comments are for *why*, not *what*.
5. Apply DRY/YAGNI consistently.

### Required Tools

```bash
black .                        # Code formatting
isort .                        # Import sorting
ruff check --fix .             # Linting
mypy --strict .                # Type checking
pytest --cov=src --cov-report=html --cov-fail-under=95
```

Pre-commit must run all these on commit. CI must reject failures.

---

## Typing & Documentation

- All functions and methods must be type hinted.
- Use `Annotated` when carrying metadata.
- Use `Protocol` to define interfaces.
- Docstrings: Google style, only for public functions.

### Example

```python
from typing import Annotated, Any
from pydantic import PositiveInt

def process_tasks(
    tasks: list[dict[str, Any]],
    max_concurrent: Annotated[PositiveInt, "Maximum concurrency"] = 5,
) -> dict[str, int]:
    """Process a list of tasks concurrently.

    Args:
        tasks: Raw task dictionaries.
        max_concurrent: How many to run in parallel.

    Returns:
        Summary dictionary with success/error counts.
    """
    return {"processed": len(tasks), "errors": 0}
```

---

## Project Structure

```text
project-root/
├── src/
│   └── task_manager/
│       ├── domain/            # Business logic
│       ├── infrastructure/    # DBs, queues, adapters
│       ├── interfaces/        # API, CLI, workers
│       ├── utils/             # Logging, validation
│       └── config.py          # Pydantic settings
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/                      # Sphinx or Markdown docs
├── docker/
├── pyproject.toml
├── poetry.lock
└── README.md
```

Each file should stay under 200 lines. Follow hexagonal architecture.

---

## Configuration

Use `pydantic-settings`:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    env: str = "dev"
    db_url: str
    jwt_secret: str
    redis_url: str

    model_config = {"env_file": ".env"}

settings = Settings()
```

---

## Logging

Use `structlog` with environment-aware processors.

```python
import structlog

def setup_logging():
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ]
    )

logger = structlog.get_logger()
```

---

## API Guidelines (FastAPI)

- Use OpenAPI defaults.
- Set `default_response_class=ORJSONResponse`.
- Middleware: CORS, GZip, RateLimit (e.g., slowapi).
- Version endpoints via `/api/v1/...`

---

## Testing Practices

- 95%+ test coverage; focus on edge behavior.
- Use `pytest-mock` to isolate side effects.
- Use `Hypothesis` for properties.
- File naming: `test_<unit>_when_<context>.py`

---

## Containerization

Dockerfile must:
- Use `python:3.12-slim`
- Install via poetry
- Run as non-root user
- Include healthcheck and expose 8000

Use multi-stage builds. Store config in `docker/compose/dev.yml`.

---

## Monitoring & Observability

- Use `opentelemetry` for tracing (FastAPI, SQLAlchemy).
- Emit metrics with Prometheus client.
- Track request IDs and trace headers in logs.

---

## Error Handling

- Subclass `Exception` into `DomainError`, `InfraError`, etc.
- Use `Result[Ok, Err]` pattern where appropriate.
- Don’t catch `Exception` broadly without logging + re-raise.

---

## Security Practices

- Inputs: validate/sanitize via Pydantic
- Secrets: via env vars / Vault
- Tests: cover auth bypass attempts
- Rate limit by IP/User ID
- Add audit logging for data-modifying endpoints

---

## Git Standards

- Feature branches: `feat/...`
- Squash commits before merge
- PRs must include:
  - Description
  - Link to issue
  - Tests + screenshots (if relevant)

---

## AI Assistant Directives

When reviewing or generating code:

1. Prioritize simplicity and explicit logic
2. Match patterns used in `src/`
3. Do not introduce globals or implicit state
4. Include full typing and meaningful variable names
5. Add tests and suggest edge case coverage
6. Keep changes under 200 LOC per file

---

## Template Version

- Version: 1.0.0
- Last Updated: 2025-07-12
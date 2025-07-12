# Contributing to Legal Parser

We welcome contributions to this project! Please follow these guidelines to ensure a smooth development process.

## Code Style & Quality

*Write the simplest code that **cannot** fail silently.*

### Language & Environment
| Item            | Standard                         |
|-----------------|----------------------------------|
| Python version  | **3.12+**                       |
| Virtual-env     | `python -m venv .venv`           |
| Dependencies    | `pip-tools` (`*.in` -> `*.txt`)  |
| OS targets      | Linux (Docker); macOS for dev    |

### Formatting & Linting
| Tool    | Purpose                    | Enforcement |
|---------|---------------------------|-------------|
| **Black** | Auto-formatter (line 88)  | `pre-commit` hook |
| **Ruff**  | Lint + import sort        | `pre-commit` hook |
| **Mypy**  | Static typing (`strict`)  | CI job          |

### Pre-commit setup
```bash
pre-commit install           # once
pre-commit run --all-files   # one-shot check
```

# Code Style & Quality Guide  
*Write the simplest code that **cannot** fail silently.*

---

## 1 · Language & Environment
| Item            | Standard                         |
|-----------------|----------------------------------|
| Python version  | **3.12 +**                       |
| Virtual-env     | `python -m venv .venv`           |
| Dependencies    | **pip-tools** (`*.in → *.txt`) <br>or **Poetry** |
| OS targets      | Linux (Docker); macOS for dev    |

---

## 2 · Formatting & Linting
| Tool    | Purpose                    | Enforcement |
|---------|---------------------------|-------------|
| **Black** | Auto-formatter (line 88)  | `pre-commit` hook |
| **Ruff**  | Lint + import sort        | `pre-commit` hook |
| **Mypy**  | Static typing (`strict`)  | CI job          |

### Pre-commit setup
```bash
pre-commit install           # once
pre-commit run --all-files   # one-shot check
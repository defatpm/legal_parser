# Debug & CI Stabilization Plan for `legal_parser`

> **Goal:** Eliminate recurring *syntax‑related* build failures on GitHub and ensure that every pull‑request is validated in <60 s locally and <5 min in CI.

---

## 1. Snapshot of Current Pain Points

| Symptom                              | Likely Cause                                                                          | Quick Triage                                                       |
| ------------------------------------ | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| \`\` during GH Action                | Lint passes locally but CI uses a *different* Python version (3.13‑dev vs. 3.11/3.12) | Pin interpreter version & run `python -m compileall` pre‑push      |
| **PyTest hangs ≥30 min**             | ‑ Infinite loop / unawaited coroutine                                                 |                                                                    |
| ‑ Network I/O in strict asyncio mode |                                                                                       |                                                                    |
| ‑ Test fixture deadlock              | Run with `pytest -vv --asyncio-mode=strict --timeout=20 --durations=25`               |                                                                    |
| **Inconsistent lint results**        | Missing pre‑commit or mis‑aligned tool versions                                       | Share `ruff`, `black`, `pyupgrade` via `pyproject.toml` + lockfile |

---

## 2. Immediate “Smoke Test” Checklist (run before every push)

```bash
# 1  Create isolated env
pyenv install 3.12.3  # once
pyenv local 3.12.3
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# 2  Lint + type‑check + static compile
ruff check legal_parser tests
mypy legal_parser  # optional but recommended
python -m compileall -q legal_parser  # catches syntax errors early

# 3  Run tests fast & loud
pytest -q -x --maxfail=1 --asyncio-mode=strict --timeout=20
```

Add this block to a shell script (`./scripts/smoke.sh`) and wire it into your pre‑commit hooks.

---

## 3. Robust Local Dev Workflow

1. **Environment parity** → Use `** + **` to standardise.
2. **Editor support** → Enable Ruff & MyPy integrations; turn on *save‑time* formatting with **Black/ Ruff format**.
3. **Pre‑commit** (add `.pre‑commit-config.yaml`):

   ```yaml
   ```

repos:

* repo: [https://github.com/astral-sh/ruff-pre-commit](https://github.com/astral-sh/ruff-pre-commit)
  rev: v0.12.3
  hooks:

  * id: ruff

    # ✨ Auto‑apply every safe fix and most unsafe ones

    args: \[--fix, --unsafe-fixes]
* repo: [https://github.com/psf/black](https://github.com/psf/black)
  rev: 25.1.0
  hooks:

  * id: black
* repo: [https://github.com/asottile/pyupgrade](https://github.com/asottile/pyupgrade)
  rev: v3.20.0
  hooks:

  * id: pyupgrade

````
   Run `pre-commit install` once.
4. **“One‑shot” compile check**: `python -m compileall -q legal_parser`.

---

## 4. Continuous Integration Pipeline (GitHub Actions)

```yaml
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-dev.txt
      - name: Lint & Type Check
        run: |
          ruff check .
          python -m compileall -q legal_parser
      - name: Run Tests
        run: |
          pytest -q --asyncio-mode=strict --timeout=60 --cov=legal_parser
````

Key points:

* **Matrix builds** catch version‑specific syntax.
* \`\` step fails fast on syntax.
* **Timeout** prevents silent test hangs.

---

## 5. Debugging Syntax Errors

1. **Reproduce exactly**: `pip install -r requirements-dev.txt && python -m compileall -q legal_parser`.
2. **Pin tooling**: Align `ruff`, `black`, `mypy` versions in `pyproject.toml`.
3. **Iterate**: Fix the offending file; rerun compile. Repeat until zero errors.
4. **Regression‑proof**: Add specific “syntax smoke” test:

   ```python
   # tests/test_compile.py
   import importlib, pkgutil
   import legal_parser

   def test_all_modules_importable():
       pkgpath = legal_parser.__path__
       for mod in pkgutil.walk_packages(pkgpath, legal_parser.__name__ + "."):
           importlib.import_module(mod.name)
   ```

---

## 6. Debugging Tests That Hang > 30 s

```bash
pytest -vv --maxfail=1 --timeout=10 --durations=10 -s
```

* \`\` (requires `pytest‑timeout`) kills rogue tests.
* \`\` surfaces slowest tests.
* Insert `or` inside suspect loops.
* For async⁠/⁠await, use \`\` to flag forgotten awaits.

---

## 7. Quality Gates (optional but recommended)

| Gate        | Tool         | Threshold        |
| ----------- | ------------ | ---------------- |
| Coverage    | `pytest-cov` | ≥ 85 %           |
| Lint errors | Ruff         | 0                |
| Complexity  | `radon cc`   | ≤ B per function |

Fail CI if gates not met.

---

## 8. Common Commands Cheat‑Sheet

```bash
# Run fastest single failing test from previous run
pytest --lf -x

# Watch mode (filesystem changes) – needs pytest-watch
ptw --onfail "notify-send 'Tests Failed'"

# Format entire project
ruff format .

# Upgrade imports to modern syntax
pyupgrade --py311-plus $(git ls-files '*.py')
```

---

## 9. Resources

* Ruff Docs → [https://docs.astral.sh/ruff/](https://docs.astral.sh/ruff/)
* PyTest “Hangs” guide → [https://docs.pytest.org/en/stable/how-to/failures.html#tests-hanging](https://docs.pytest.org/en/stable/how-to/failures.html#tests-hanging)
* GitHub Actions Python → [https://github.com/actions/setup-python](https://github.com/actions/setup-python)

---

### ✅ Next Steps for You

1. Commit this `DEBUG_PLAN.md` to the repo.
2. Add `.python-version` (e.g., `3.12.3`).
3. Install & configure **pre‑commit** (`pre-commit install`).
4. Copy the CI template into `.github/workflows/ci.yml`.
5. Push; verify that CI is green in <5 min.

Feel free to iterate—open an issue or PR if adjustments are needed!

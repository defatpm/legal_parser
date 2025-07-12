# code_fix.md — Resolve Pytest CI Build Errors

## 🌟 Goal

Fix GitHub Actions CI failure due to unrecognized pytest arguments:
- `--asyncio-mode=strict`
- `--timeout=60`

These flags are used in `.github/workflows/ci.yml` but the required pytest plugins are missing from `requirements-dev.txt`.

---

## ✅ Instructions

### 1. Edit `requirements-dev.txt`

Ensure the following packages are added:
```
pytest-asyncio>=0.21.0
pytest-timeout>=2.1.0
```

### 2. Reinstall dependencies
```bash
pip install -r requirements-dev.txt
```

### 3. Run tests to confirm fix
```bash
pytest --asyncio-mode=strict --timeout=60
```

Tests must pass without flag errors.

---

## 📤 4. Commit & Push

If the above steps succeed:

```bash
git add requirements-dev.txt
git commit -m "fix: add pytest plugins to support asyncio-mode and timeout flags"
git push origin main
```

---

## ✅ Success Criteria

- GitHub Actions workflow succeeds on push.
- No more errors related to `--asyncio-mode` or `--timeout`.

---

## 🤖 Gemini CLI Usage

To execute this plan autonomously, run:

```bash
gemini review-and-execute code_fix.md
```

This will:
- Read and apply the required edits
- Install dependencies
- Validate with tests
- Commit and push if successful

No manual intervention required.

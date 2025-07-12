# Project Context for Claude CLI

---


## Related Language-Specific Standards

For extended language-specific rules, refer to:

| Language   | Reference File                                    |
| ---------- | ------------------------------------------------- |
| Python     | [python-CLAUDE.md](./python-CLAUDE.md)            |
| TypeScript | [ts-CLAUDE.md](./ts-CLAUDE.md) *(optional)*       |
| Legal Tech | [CLAUDE-legal.md](./CLAUDE-legal.md) *(optional)* |

---

## Getting Started (First Time Setup)

1. **Prerequisites:** [e.g., Node 18+, Python 3.12+, Docker]
2. **Clone:** `git clone [repo-url]`
3. **Install:** `npm install` / `pip install -r requirements.txt`
4. **Configure:** Copy `.env.example` to `.env`
5. **Run:** `npm run dev` / `python manage.py runserver`
6. **Verify:** Open [http\://localhost:3000]

---

## Quick Commands

```bash
# Setup
make install        # or npm install / pip install

# Development
make dev            # Start development server
make test           # Run tests
make lint           # Check code quality
make format         # Auto-format code

# Deployment
make build          # Build for production
make deploy         # Deploy to production
```

---

## Code Standards

### Universal Rules

1. Functions should not exceed 20 lines.
2. Files should not exceed 200 lines.
3. Use descriptive names; avoid abbreviations.
4. Only document complex business logic.
5. Always write tests before implementation.

### Language-Specific Guidelines

#### JavaScript / TypeScript

- Use TypeScript: Strict types, no `any`.
- Enforce ESLint + Prettier.
- Use async/await.
- Prefer modules over globals.
- Graceful error handling via try/catch.

#### Python

- Enforce PEP 8/257 with type hints.
- Google-style docstrings.
- Prefer `pathlib`, `:=`, `f-strings`.
- Avoid mutable default arguments.
- Use generators where efficient.

---

## Project Structure

```text
src/
├── components/     # UI components (React/Vue)
├── services/       # Business logic modules
├── utils/          # Shared helpers/utilities
├── types/          # Type definitions (TS or Python)
├── entry.ts/py     # Entry point
├── tests/          # Unit/integration tests
└── config/         # App configuration
```

---

## Development Workflow

### Git Flow

- Feature branches: `feat/user-auth`
- Use [Conventional Commits](https://www.conventionalcommits.org/)
- PRs must:
  - Link issues
  - Explain What/Why/How
  - Be reviewed before merge
- Rebase or squash to keep history clean

### Code Quality

Run these before any commit or PR:

```bash
# Format
npm run format      # JS/TS
black . && isort .  # Python

# Lint
npm run lint        # JS/TS
ruff check --fix .  # Python

# Type Check
npm run type-check  # JS/TS
tsc --noEmit        # TypeScript
mypy --strict .     # Python

# Tests
npm test -- --coverage  # Jest
pytest --cov --cov-fail-under=90  # Python
```

Use Husky or pre-commit to automate.

---

## Testing Standards

- 90%+ meaningful test coverage.
- Unit: Pure functions.
- Integration: Service and adapter boundaries.
- E2E: Simulated real-world workflows.
- Tools: Jest + Cypress / Pytest + Hypothesis.
- Naming: `test_service_fails_when_input_invalid`.

---

## Documentation Requirements

- **README:** Setup, usage, architecture diagram.
- **CHANGELOG:** Maintain with [Keep a Changelog](https://keepachangelog.com/)
- **Inline Docs:** Only where reasoning is not obvious.
- **APIs:** JSDoc, Sphinx, or Typedoc with examples.
- **Sites:** MkDocs, Docusaurus for live documentation.

---

## Deployment & Infrastructure

### Env Vars

- `ENV`: dev / prod
- `API_URL`, `DB_URL`, `SECRET`, etc.

### Process

1. Local quality checks
2. Version bump
3. Build + test
4. Deploy to staging
5. Manual QA if required
6. Promote to prod

Use Docker/Kubernetes where applicable. Ensure rollback plan.

---

## Security Considerations

- Never commit secrets. Use `.env` or secrets manager.
- Validate all inputs.
- Use HTTPS, auth headers, rate limits.
- Regular `npm audit` / `pip-audit`.
- Periodic vulnerability scanning.

---

## Performance Guidelines

- Optimize LCP/FID/CLS (frontend).
- Lazy load + caching (Redis/CDN).
- Use efficient algorithms and data structures.
- Profile: Chrome DevTools, py-spy, cProfile.

---

## Common Issues

- **Port already in use:** Change PORT in .env
- **Module not found:** Run install again
- **DB errors:** Check credentials in `.env`
- **Broken styles:** Clear browser cache / rebuild assets

---

## Code Review Checklist

-

---

## AI Assistant Guidelines

When working on this project:

1. Follow code standards strictly
2. Always write tests for new features
3. Use consistent patterns
4. Ask for clarification if scope is ambiguous
5. Suggest performance/security improvements
6. Keep entropy low; explain refactors

---

## Domain Context (Optional)

### Legal/Compliance Requirements

-

---

## Template Version

- **Version:** 2.0.0
- **Last Updated:** 2025-07-12
- **Changelog:** See `TEMPLATE_CHANGELOG.md` for history
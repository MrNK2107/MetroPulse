# Contributing to MetroPulse

Thanks for helping. This file covers setup, tests and what a pull request needs. Architecture decisions
are recorded in `docs/adr/`; read those before changing how the core loop, data import or API work.

## Setup

Backend (Python 3.11+):

```bash
cd backend
python -m venv .venv && . .venv/Scripts/activate   # or .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
uvicorn app.main:app --reload --port 8000
```

Twin data: `cd backend && python scripts/twin_build.py check` (or `build`).

Frontend (Node 20):

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

See `SETUP.md` for environment variables and optional services.

## Tests

- Backend: `cd backend && pytest tests/unit tests/integration`. Tests never touch the network; mock HTTP
  with `httpx.MockTransport` and mark a deliberate live test with `@pytest.mark.allow_network`.
- Frontend: `cd frontend && npm run test` (CI runs `npm run test:ci`; locally `--maxWorkers=2` keeps it
  light).
- Lint and types: `cd frontend && npm run lint && npm run type-check`.

## How we work

- **Test first.** Write the failing test, watch it fail, then write the code that makes it pass. Bug fixes
  start with a test that reproduces the bug.
- **Numbers show their working.** Any new figure on screen shows its formula and inputs.
- **Your data stays in the browser.** Nothing a user loads is uploaded.
- **Conventions:** TypeScript strict mode, camelCase props, PascalCase components; NumPy vectorised ops in
  Python where arrays are involved; API responses use the `{ success, data, error, meta }` envelope.

## Commits

Use `type(scope): description`, for example `feat(twin): add place index` or `fix(desk): keep hub order`.
Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `perf`, `ci`.

## Pull request checklist

- [ ] Tests added or updated, and written before the change
- [ ] Backend and frontend test suites pass locally
- [ ] `npm run lint` and `npm run type-check` pass
- [ ] Commits follow `type(scope): description`
- [ ] Docs updated (README, `docs/`, an ADR if a decision changed)
- [ ] No secrets, tokens or personal data in the diff

By contributing you agree that your contribution is licensed under the Apache License 2.0 (`LICENSE`).

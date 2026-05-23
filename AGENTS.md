# MetroPulse — Agent Context

## Project
AI-Powered Macro-Urban Digital Twin Sandbox. Next.js 14 (frontend) + FastAPI (backend) + Supabase PostgreSQL + pgvector.

## Commands
- Backend: `cd backend && uvicorn app.main:app --reload --port 8000`
- Backend tests: `cd backend && pytest`
- Frontend: `cd frontend && npm run dev`
- Frontend tests: `cd frontend && npm run test`
- Lint/typecheck: `cd frontend && npm run lint && npm run type-check`

## Conventions
- Python: Use NumPy vectorized ops, no Python loops over cells in sim engine
- TypeScript: strict mode, camelCase props, PascalCase components
- All API responses use `{ success, data, error, meta }` envelope
- Simulation engine: NO database writes mid-loop, batch-save only after completion
- Commit format: `type(scope): description` (e.g. `feat(engine): add primary loop`)

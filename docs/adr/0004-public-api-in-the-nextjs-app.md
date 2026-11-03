# 0004. The public JSON API lives in the Next.js app as route handlers

**Status:** Accepted (2026-11-03)

## Context

2.0 adds a documented JSON API: the city list, a city's briefing numbers, its incidents, a site score,
station suggestions and a line scenario. Those answers come from the core loop, which is TypeScript in
the frontend (ADR 0001). Serving them from the FastAPI backend would mean porting the loop to Python or
calling Node from Python, and keeping two implementations bit-identical, which is the failure ADR 0001
exists to prevent.

## Decision

The API is a set of `/api/v1/*` route handlers in the Next.js app, calling the same `lib/pulse` code the
desk uses. Responses use the house envelope `{ success, data, error, meta }`; errors are
`{ success: false, error: { code, message } }` with 400 or 404, and unknown routes under `/api/v1` return
a 404 envelope. Read endpoints are GET with `Cache-Control: public, max-age=3600` and open CORS. The
`/developers` page documents them. The FastAPI backend keeps what it already owns: the India Twin
(`/api/twin/*`), ingest, and the token-gated planning agent (`/ws/agent`).

## Consequences

- One implementation of every number: the API, the city pages and the desk cannot disagree.
- The API deploys with the frontend and needs no extra service.
- There is no rate limit in the app; the hosting platform's limit applies, and the docs page says so.
- Two backends exist with different jobs. Anything that needs the core loop belongs in Next.js; anything
  that needs Python data tooling or the agent stays in FastAPI.

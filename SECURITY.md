# Security policy

## Reporting a vulnerability

Email **GitHub's private vulnerability reporting on this repository (Security tab → Report a vulnerability). It reaches the maintainers without a public issue.
reproduce. Please do not open a public issue for a vulnerability. We aim to acknowledge a report within
three working days and to agree a disclosure date with you before anything is published.

> This address is a placeholder until the owner confirms a monitored inbox (see `NEEDS_INPUT.md`). Until
> then, use GitHub's private vulnerability reporting on this repository.

## Supported versions

| Version | Supported |
|---------|-----------|
| 2.x     | Yes       |
| 1.x and earlier | No |

## Token model

MetroPulse has no user accounts. Two shared tokens, both read from the backend environment, gate the
only endpoints that act on input beyond a lookup:

- **`AGENT_WS_TOKEN`** gates the planning-agent WebSocket `/ws/agent`. When it is unset the endpoint is
  off: every connection is closed with code 1008 before it is accepted. When it is set, clients send it as
  `?token=` or `Authorization: Bearer <token>`; it is compared in constant time (`hmac.compare_digest`).
  At most `WS_MAX_CONNECTIONS` sessions (default 10) run at once; extras close with 1013. Errors sent to
  the client are generic and never carry exception text.
- **`INGEST_TOKEN`** optionally gates `POST /api/ingest`. When it is unset the endpoint is open; when it
  is set, requests need `Authorization: Bearer <token>` or `X-Ingest-Token: <token>` (constant-time
  compare, 401 otherwise). Deployments that expose the backend publicly should set it.

Per-user authentication for `/ws/agent` is not yet built; the shared token is the interim gate.

## Your own data

The desk's own-data feature (city boundary, stations, observed counts) runs entirely in the browser.
Files you load are parsed client-side and never uploaded; there is no upload endpoint. Only derived data
(the boundary ring, a station list, per-station daily counts) is kept, in the browser's `localStorage`,
and clearing it from the desk or the browser removes it.

## Tests

The backend test suite never touches the network: `backend/tests/conftest.py` blocks every non-loopback
connection, so a test cannot leak data or depend on a live service by accident.

## Workspaces (optional)

When `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` are set, the desk offers magic-link
sign-in and syncs saved lines to a `scenarios` table. The anon key is public; access is enforced by
row-level security (`supabase/migrations/010_scenarios.sql`): a user reads and writes only rows where
`user_id = auth.uid()`. Nothing a user loads under Your data (boundary, stations, counts, zones) is
sent to the workspace; only saved lines are.

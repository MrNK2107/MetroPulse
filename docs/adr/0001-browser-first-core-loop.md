# 0001. The core loop is deterministic TypeScript in the browser

**Status:** Accepted (2026-11-03)

## Context

The desk's loop (see, notice, decide, persuade) builds a demand field over a hex grid for a city, scores
candidate sites, suggests stations and writes the briefing. Planners use it while talking a client through
options, so a change has to show its result at once, and the same inputs must always give the same
numbers: a figure quoted in a DPR draft cannot drift between two page loads. The same numbers are also
rendered on the server (city pages, the API) and in the browser, and a mismatch between the two would be
visible to anyone comparing them.

## Decision

The core loop is plain TypeScript in `frontend/src/lib/pulse/`. It makes no network calls, uses no
unseeded randomness, and does not depend on the Python backend. It runs client-side in about a second per
city. Server render and browser render use the same code and the same hex-grid rounding rule, so their
output is bit-identical. Every figure it produces carries its formula and inputs so the screen can show
its working.

## Consequences

- The desk works once loaded without further requests and costs nothing to serve per user.
- Results are reproducible: a saved scenario re-opens to the same numbers.
- The loop is limited to what a browser can compute in about a second; a heavier model (a real OD-based
  demand field) needs a different design and a new record.
- The FastAPI backend is not on the desk's critical path; it keeps the India Twin data and the agent.
- Tests for the loop are fast Jest tests on pure functions, with no mocks for network or storage.

# India Twin: Roadmap of Plans

**Spec:** `docs/superpowers/specs/2026-10-18-india-twin-design.md`
**Branch:** `feat/india-twin`

The spec has seven milestones (§7), and each one depends on what the previous one produced. Each milestone gets its **own detailed plan**, written when the previous milestone is merged. The later plans can then use real names, real data quirks and real test results instead of guesses.

| # | Milestone | Plan | Status | Exit check (what the owner can try) |
|---|---|---|---|---|
| M1 | Backbone | `2026-10-18-india-twin-m1-backbone.md` | **ready** | Map of all India's districts with official borders. Search "Gaya" → click → population (Census 2011, re-apportioned to today's districts) and nightlights, each with a source receipt. |
| M2 | Ask anything (facts and analysis) + login, roles, rate limits, safety gate, logging | written after M1 | — | Lookup and analysis questions answered across all districts, with receipts. Benchmark v1 (~100 questions) runs in local mode. Sign-in works. Limits are enforced. |
| M3 | Wiring: connections graph + episodes library + admin edge review | written after M2 | — | "What depends on US demand?" shows a graph explorer on the map. 25 episodes loaded with elasticities. |
| M4 | Scenario engine | written after M3 | — | The US question produces a streamed tree with ranged, sourced numbers. 3 backtests reported. |
| M5 | Cinematic scenario screen | written after M4 | — | The approved `combined-v1` screen, playing for real. |
| M6 | Depth and polish | written after M5 | — | City packs, 300-question benchmark, neutrality evaluations, performance targets met, mobile layout, admin dashboards. |
| M7 | Launch-ready (still local) | written after M6 | — | One config flip to cloud mode, load test, security review, deploy dry-run, runbook. |

## Placed on the roadmap so nothing in the spec is dropped

- **Self-hosted basemap tiles (roads, water, labels) with OSM borders removed (spec §4):** M2.
  - M1 deliberately draws **no basemap at all**, only our own SoI-aligned national, state and district layers on a dark background. That already satisfies the border rule.
- **Local embeddings and the vector-size migration (spec §4):** M2, alongside the indicator search that needs them.
- **Single-worker GPU queue for local AI calls (spec §4):** M2. That's the first milestone that calls a model.
- **Live weather and air quality (spec §5.9):** M2.
- **WorldPop population weights for the crosswalk (spec §5.1):** M1 builds the weighting hook. M2 loads WorldPop and switches Census apportioning from area to population weights.
- **WebSocket connection limit for /ws/agent (was enforced only by the retired simulator WS):** M2, with rate limiting.

## How each plan gets written

When a milestone merges, run `superpowers:writing-plans` against the spec plus this roadmap. Record anything the milestone learned that changes later milestones in the **Learned** section below.

## Learned

_(empty, filled in as milestones complete)_

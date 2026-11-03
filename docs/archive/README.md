# Archive

These documents describe earlier versions of MetroPulse. They are kept for reference, not maintained, and
may contradict the current code. The current product is described in the root `README.md`,
`docs/PRODUCT.md`, `docs/ARCHITECTURE.md` and `docs/adr/`. Git history has the full context for each
file (`git log --follow docs/archive/<file>`), and the tag `legacy-metropulse` marks the last commit with
the city simulator intact.

**`2026-05-spec-simulator.md`** (was `SPEC.md`). The 1.0 engineering specification for the original
product, an "AI-powered macro-urban digital twin sandbox" in which sliders drove a Python city simulator.
Archived because that product was retired (see ADR 0003) and the spec no longer describes anything in the
tree.

**`2026-05-implementation-plan-simulator.md`** (was `IMPLEMENTATION_PLAN.md`). The 25-day phased build
plan for that simulator. Archived with the spec it implemented; none of its phases apply to the desk.

**`2026-10-status.md`** (was `status.md`). A project status snapshot from the 2026-10-20 night run, early
in the India Twin era, with test counts and open items as they stood then. Archived because its numbers
are historical; current status is in the README and the changelog.

**`night-runs.md`** (was `NIGHT_RUN_NOTES.md`). Running notes from the unattended night runs of October
and early November 2026: what each run changed, what it verified and what it left open. Archived as a
work log; the changes themselves are in history and `CHANGELOG.md`.

**`INDIA_OVERHAUL_PLAN.md`** (was `docs/INDIA_OVERHAUL_PLAN.md`). The May 2026 plan to rewrite the
simulation engine around Indian cities and an India data pipeline. Archived because the simulator it
overhauled was retired; the India data work continued as the India Twin.

**`RAG_ENGINE.md`** (was `docs/RAG_ENGINE.md`). Documentation of the retrieval engine (`backend/app/rag/`)
that supplied case-study evidence and confidence scores to the simulator. Archived because the module was
parked and is removed in 2.0.

**`2026-05-26-scenario-driven-simulation-design.md`** (was in `docs/superpowers/specs/`). The design that
replaced the slider model with scenario-driven simulation. Archived with the simulator it designed.

**`2026-05-28-nl-simulation-design.md`** (was in `docs/superpowers/specs/`). The design for natural
language "what if?" economic scenarios with an intent router, a conversation manager and social group
scoring. Archived because the natural-language simulator was retired.

**`2026-05-28-nl-simulation.md`** (was in `docs/superpowers/plans/`). The task-by-task implementation plan
for that natural-language simulation design. Archived with its spec.

# 0003. The retired city simulator is removed from the repository

**Status:** Accepted (2026-11-03)

## Context

MetroPulse began as a city simulator: sliders and natural-language scenarios driving a Python economic
model, with a RAG engine for explanations. The product moved to the India Twin and then to the planning
desk, and the simulator was retired, but its modules (`app/rag/`, `app/simulation/`, parts of `engine/`
and `nl_engine/`), a 25-day implementation plan and a spec for that product stayed in the tree. New
contributors read them as current, tests kept them alive, and the repository looked like two products.

## Decision

The dormant simulator code is deleted together with its tests. The few pieces still used elsewhere move
to where they are used (for example `app/simulation/llm.py` becomes `app/llm.py`). The simulator-era
documents move to `docs/archive/` with an index saying what each was. The git tag `legacy-metropulse`
marks the last commit with the simulator intact and is the reference for anyone who needs the old code.
Nothing from the simulator comes back into the product.

## Consequences

- The tree and the test suite describe one product; the backend suite shrinks to code that runs.
- The old design stays recoverable from `legacy-metropulse` and from history, but it is no longer
  maintained or tested.
- The parked planning agent (`engine/agent/`, `/ws/agent`) stays; it is not part of the simulator.
- Any future scenario modelling is designed fresh against the desk, not revived from the archive.

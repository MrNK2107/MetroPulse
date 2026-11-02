# India Twin M1: Backbone Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every district in India sits on one shared place backbone (LGD codes, SoI-aligned boundaries, a 2011→current crosswalk, an aliases table and H3 links). A versioned data pipeline publishes Census 2011 and VIIRS nightlights onto it, served through an API and a dark India map where you can search a district, click it, and see sourced values.

**Architecture:**
- **`backend/twin/`** is a new pure package, like `engine/`, with no imports from `app/`. Its parts:
  - `places/`: backbone builders and the resolver
  - `pipeline/`: adapter framework plus the LGD, Census and VIIRS adapters
  - `store/`: the shared observation schema, Parquet storage read with DuckDB, the indicator catalogue, and an optional Postgres sync
- **`app/routes/twin.py`** serves the published data under `/api/twin`.
- **The old city simulator is retired** at the end of the milestone. The frontend `/` becomes the new India map.

**Tech Stack:** Python 3.11+, FastAPI, pandas, geopandas, shapely, rasterio, h3 4.x, rapidfuzz, pyarrow, DuckDB, and Supabase Postgres + PostGIS (sync only). Frontend: Next.js 14, deck.gl 9 `GeoJsonLayer` (no basemap), Zustand and Jest.

**Spec:** `docs/superpowers/specs/2026-10-18-india-twin-design.md` (§4, §5.1, §5.2, §6, §7 M1). Roadmap: `docs/superpowers/plans/2026-10-18-india-twin-roadmap.md`.

## Global Constraints

- Engine-style packages (`engine/`, `twin/`) never import from `app/`. Callbacks and paths are passed in (AGENTS.md).
- Every API response uses the `{ success, data, error, meta }` envelope.
- Commit format is `type(scope): description`. Every commit ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Borders follow the official Survey of India boundary. **No third-party basemap or tiles in M1.** Only our own national, state and district layers are drawn.
- Every value carries `source_id`, `dataset_version`, its observation period and a trust label (`fact` | `pattern` | `projection`).
- When data is missing it's shown as missing (`null` plus "No data"), never as `0`.
- Data licences are respected. Each source is listed in `SOURCE_REGISTRY` with its licence.
- Tests never touch the network. They use fixtures in `backend/tests/fixtures/twin/`.
- Python: use NumPy, pandas or geopandas vectorised operations, not per-row Python loops over cells or pixels.
- The data root is `TWIN_DATA_DIR` (default `<repo>/data/twin`). `manual/`, `raw/` and `published/` under it are gitignored, and `seed/` is committed.

## Review Focus

1. **Duplicate district names across states** (Aurangabad in Bihar and Maharashtra; Bilaspur, Hamirpur, Pratapgarh, Raigarh). The resolver must return all candidates and flag them as ambiguous, never silently pick one. *Test: Task 3 `test_ambiguous_name_returns_all_candidates`.*
2. **Districts split since 2011.** Census values must be apportioned across the new districts, never copied into each one. The national total must be conserved. *Test: Task 5 `test_split_district_conserves_total`, Task 9 `test_national_population_conserved`.*
3. **Districts with no value for an indicator.** The API returns `value: null`, and the card shows "No data" instead of 0. *Tests: Task 12 `test_missing_value_is_null_not_zero`, Task 13 `PlaceCard shows No data for null`.*
4. **Tiny districts and islands** (Lakshadweep, Mahe, Nicobar) that contain no H3 cell centre at resolution 5 must still get at least one cell. *Test: Task 6 `test_tiny_island_district_gets_a_cell`.*
5. **Re-running the pipeline on the same files** must not create a duplicate version. A changed file creates a new version and keeps the old one. *Test: Task 7 `test_rerun_same_input_is_idempotent`, `test_changed_input_creates_new_version`.*

---

## File Structure

```
backend/
  twin/
    __init__.py
    paths.py                  # TwinPaths: data root layout
    store/
      __init__.py
      schema.py               # Observation columns, TrustLabel, place_id helpers, validate_observations()
      parquet_store.py        # write/read published datasets; DuckDB queries; CURRENT.json pointer
      catalog.py              # Indicator dataclass, catalogue read/write, search_indicators()
      pg_sync.py              # optional upsert of places/indicators/dataset_versions to Postgres
    places/
      __init__.py
      normalize.py            # normalize_name()
      lgd.py                  # LGD CSV → places DataFrame
      resolver.py             # PlaceResolver, PlaceMatch, Resolution
      boundaries.py           # SoI shapefile → boundaries GeoDataFrame per level, clip, simplify
      crosswalk.py            # build_crosswalk(), apply_crosswalk()
      h3link.py               # build_h3_index()
      build.py                # build_backbone(): orchestrates the places/* steps
    pipeline/
      __init__.py
      base.py                 # SourceAdapter protocol, PipelineContext, ValidationReport, run_pipeline()
      census2011.py           # Census 2011 PCA district adapter
      viirs.py                # VIIRS annual nightlights adapter
  app/routes/twin.py          # /api/twin/* endpoints
  scripts/twin_build.py       # CLI: build backbone + run adapters on files in data/twin/manual
  tests/unit/twin/...         # one test file per module
  tests/integration/test_twin_api.py
  tests/fixtures/twin/        # tiny CSVs, GeoJSONs, generated rasters
data/twin/seed/aliases.csv    # committed
data/twin/manual/README.md    # committed: exact files the owner downloads
supabase/migrations/008_dataset_versions.sql   # trimmed from the parked 008
supabase/migrations/009_twin_places.sql
frontend/src/
  types/twin.ts
  lib/twinApi.ts
  store/twinStore.ts
  components/twin/IndiaMap.tsx
  components/twin/PlaceSearch.tsx
  components/twin/PlaceCard.tsx
  app/page.tsx                # replaced
docs/twin/DATA_SOURCES.md
```

---

### Task 0: Branch housekeeping (legacy tag, park swarm, bring keepers)

**Files:**
- Modify: `backend/app/main.py` (remove `projects_router` and `runs_ws_router` imports and includes)
- Create: `supabase/migrations/008_dataset_versions.sql`
- Modify: `.gitignore`

**Interfaces:** Produces a clean `feat/india-twin` where the following are tracked:
- `app/data_registry.py`
- `app/source_ingestion.py`
- `app/simulation/llm.py`
- `engine/agent/`
- `app/ws/agent.py`
- the `llm_fn` changes

Swarm work lives only on `wip/swarm-and-agent`.

- [ ] **Step 1: Tag the legacy state**

```bash
git tag legacy-metropulse main
```

- [ ] **Step 2: Snapshot all uncommitted work to the parking branch**

```bash
git switch -c wip/swarm-and-agent
git add -A -- . ':!graphify-out' ':!.understand-anything' ':!.impeccable'
git commit -m "chore(wip): snapshot swarm, pixel UI and agent work before India Twin"
git switch feat/india-twin
```

Expected: `git status` on `feat/india-twin` shows only the untracked `graphify-out/`, `.understand-anything/` and `.impeccable/`.

- [ ] **Step 3: Bring the keepers onto `feat/india-twin`**

```bash
git checkout wip/swarm-and-agent -- \
  backend/app/data_registry.py backend/app/source_ingestion.py backend/app/simulation/llm.py \
  backend/app/simulation/__init__.py backend/app/ws/agent.py backend/engine/agent \
  backend/engine/prediction_generator.py backend/engine/runner.py backend/engine/overlay.py \
  backend/app/ws/simulation.py backend/app/config.py backend/app/main.py \
  backend/pyproject.toml backend/requirements.txt \
  backend/tests/unit/test_data_registry.py backend/tests/unit/test_source_ingestion.py
```

- [ ] **Step 4: Unhook parked modules from `main.py`**

Delete the imports and the `include_router` lines for `projects_router` (`app.routes.projects`) and `runs_ws_router` (`app.ws.runs`). Keep `agent_ws_router`.

- [ ] **Step 5: Create `supabase/migrations/008_dataset_versions.sql`**

It contains only the `dataset_versions` table, copied verbatim from the parked `008_projects_swarm.sql`, plus `CREATE EXTENSION IF NOT EXISTS pgcrypto;`.

- [ ] **Step 6: Add to `.gitignore`**

```
graphify-out/
.understand-anything/
data/twin/manual/
data/twin/raw/
data/twin/published/
```

- [ ] **Step 7: Run the backend suite**

Run: `cd backend && pytest tests/unit tests/integration -q`

Expected: all pass, and `test_swarm.py` is absent. If any test imports a parked module, the test belongs to the parked work: delete it on this branch.

- [ ] **Step 8: Commit**

```bash
git add -A -- backend supabase/migrations/008_dataset_versions.sql .gitignore
git commit -m "chore(repo): park swarm work, keep registry, ingestion and agent for India Twin"
```

---

### Task 1: Twin package, paths, dependencies and the observation schema

**Files:**
- Create: `backend/twin/__init__.py`, `backend/twin/paths.py`, `backend/twin/store/__init__.py`, `backend/twin/store/schema.py`
- Modify: `backend/pyproject.toml`, `backend/requirements.txt` (add `duckdb>=1.1,<2.0`, `pandas>=2.2,<3.0`, `pyarrow>=15,<25`, `geopandas>=1.0,<2.0`, `shapely>=2.0,<3.0`, `rasterio>=1.3,<2.0`, `rapidfuzz>=3.6,<4.0`)
- Modify: `backend/app/config.py` (add `twin_data_dir: str = Field(default="", alias="TWIN_DATA_DIR")`)
- Test: `backend/tests/unit/twin/__init__.py`, `backend/tests/unit/twin/test_schema.py`

**Interfaces:**
- Produces:
  - `TwinPaths(root: Path)` with these properties:
    - `.manual`, `.raw`, `.published`, `.seed`
    - `.places_dir(boundary_version: str) -> Path`
    - `.dataset_dir(source_id: str, dataset_version: str) -> Path`
    - `.current_file` (`published/CURRENT.json`)

    Also `TwinPaths.default() -> TwinPaths`, which reads the `TWIN_DATA_DIR` environment variable or falls back to `<repo>/data/twin`.
  - `OBSERVATION_COLUMNS: tuple[str, ...] = ("indicator", "place_id", "period", "value", "unit", "source_id", "dataset_version", "trust_label")`
  - `TrustLabel = Literal["fact", "pattern", "projection"]`
  - `place_id(level: str, code: str) -> str` returns `f"{level}:{code}"`. Levels are `"country"`, `"state"`, `"district"`, `"census2011_district"`, `"h3r5"`, `"h3r7"`.
  - `parse_place_id(pid: str) -> tuple[str, str]`
  - `validate_observations(df: pd.DataFrame) -> list[str]` returns a list of problems. An empty list means the data is valid.

- [ ] **Step 1: Write the failing tests**

```python
import pandas as pd
from twin.store.schema import OBSERVATION_COLUMNS, place_id, parse_place_id, validate_observations

def _row(**kw):
    base = dict(indicator="population_total", place_id="district:188", period="2011", value=1.0,
                unit="persons", source_id="census2011-pca", dataset_version="v1", trust_label="fact")
    base.update(kw); return base

def test_place_id_round_trip():
    assert place_id("district", "188") == "district:188"
    assert parse_place_id("h3r7:872830828ffffff") == ("h3r7", "872830828ffffff")

def test_valid_frame_has_no_problems():
    assert validate_observations(pd.DataFrame([_row()])) == []

def test_null_value_is_allowed():
    assert validate_observations(pd.DataFrame([_row(value=None)])) == []

def test_bad_trust_label_and_missing_column_reported():
    df = pd.DataFrame([_row(trust_label="guess")]).drop(columns=["unit"])
    problems = validate_observations(df)
    assert any("unit" in p for p in problems)
    assert any("trust_label" in p for p in problems)

def test_duplicate_key_reported():
    df = pd.DataFrame([_row(), _row()])
    assert any("duplicate" in p for p in validate_observations(df))
```

The duplicate key is `(indicator, place_id, period, dataset_version)`.

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `cd backend && pytest tests/unit/twin/test_schema.py -v`

Expected: FAIL with `ModuleNotFoundError: twin`.

- [ ] **Step 3: Implement `paths.py`, `schema.py` and the dependency and config additions** as specified in Interfaces. Install with `pip install -r requirements.txt`.

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `cd backend && pytest tests/unit/twin/test_schema.py -v`

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git commit -am "feat(twin): add twin package, data paths and observation schema"
```

(Use `git add` for the new files first.)

---

### Task 2: LGD places loader

**Files:**
- Create: `backend/twin/places/__init__.py`, `backend/twin/places/normalize.py`, `backend/twin/places/lgd.py`
- Create fixtures:
  - `backend/tests/fixtures/twin/lgd_states.csv`: 3 states (Bihar 10, Maharashtra 27, Lakshadweep 31)
  - `backend/tests/fixtures/twin/lgd_districts.csv`: Gaya, Aurangabad (BR), Patna, Aurangabad (MH, current name "Chhatrapati Sambhajinagar"), Mumbai, Lakshadweep, plus one district created after 2011 with an empty Census code
- Test: `backend/tests/unit/twin/test_lgd.py`, `backend/tests/unit/twin/test_normalize.py`

**Interfaces:**
- Produces:
  - `normalize_name(s: str) -> str`. It applies these rules in order:
    1. NFKD, then ASCII fold
    2. lowercase
    3. `&` → `and`
    4. remove the characters `.,'()-/`
    5. collapse whitespace
    6. strip a leading `the `
    7. strip trailing ` district`, ` dist`, ` zila`, ` jilla`
  - `LGD_COLUMNS: dict[str, str]` maps the LGD export headers to our column names. Expected headers are `State Code`, `State Name (In English)`, `District Code`, `District Name (In English)` and `Census 2011 Code`. If the real export differs, change only this dict and the fixture.
  - `load_lgd(states_csv: Path, districts_csv: Path, boundary_version: str) -> pd.DataFrame`
    - Columns: `place_id`, `level`, `lgd_code`, `name`, `name_norm`, `parent_id`, `state_code`, `census2011_code` (nullable str), `boundary_version`
    - Includes one `country:IN` row.
    - Raises `ValueError` on duplicate `lgd_code` within a level.

- [ ] **Step 1: Write the failing tests**

```python
from twin.places.normalize import normalize_name
from twin.places.lgd import load_lgd

def test_normalize_rules():
    assert normalize_name("  Gaya District ") == "gaya"
    assert normalize_name("Jammu & Kashmir") == "jammu and kashmir"
    assert normalize_name("Tiruchirāppalli") == "tiruchirappalli"
    assert normalize_name("The Nilgiris") == "nilgiris"

def test_lgd_builds_hierarchy(fx):  # fx = fixture dir
    df = load_lgd(fx / "lgd_states.csv", fx / "lgd_districts.csv", "lgd-test")
    gaya = df[(df.level == "district") & (df.name_norm == "gaya")].iloc[0]
    assert gaya.parent_id == "state:10"
    assert df[df.level == "state"].parent_id.eq("country:IN").all()
    assert (df.level == "country").sum() == 1

def test_new_district_has_null_census_code(fx):
    df = load_lgd(fx / "lgd_states.csv", fx / "lgd_districts.csv", "lgd-test")
    assert df[df.level == "district"].census2011_code.isna().sum() == 1
```

Define `fx` in `backend/tests/unit/twin/conftest.py` as `Path(__file__).parents[2] / "fixtures" / "twin"`.

- [ ] **Step 2: Run the tests and confirm they fail.** Run: `pytest tests/unit/twin/test_lgd.py tests/unit/twin/test_normalize.py -v`. Expected: FAIL (module missing).
- [ ] **Step 3: Implement `normalize.py` and `lgd.py`** as specified.
- [ ] **Step 4: Run the tests and confirm they pass.** Run the same command. Expected: 4 passed.
- [ ] **Step 5: Commit.** `git commit -m "feat(twin): load LGD states and districts into place hierarchy"`

---

### Task 3: Aliases and the place resolver

**Files:**
- Create: `data/twin/seed/aliases.csv` with columns `alias,canonical,state_code` (`state_code` is optional). Seed it with at least:
  - gurgaon→gurugram (06)
  - allahabad→prayagraj (09)
  - faizabad→ayodhya (09)
  - aurangabad→chhatrapati sambhajinagar (27)
  - osmanabad→dharashiv (27)
  - hoshangabad→narmadapuram (23)
  - bangalore urban→bengaluru urban (29)
  - bangalore rural→bengaluru rural (29)
  - mysore→mysuru (29)
  - belgaum→belagavi (29)
  - gulbarga→kalaburagi (29)
  - mewat→nuh (06)
  - bombay→mumbai (27)
  - calcutta→kolkata (19)
  - madras→chennai (33)
  - trichy→tiruchirappalli (33)

  The canonical side is normalised.
- Create: `backend/twin/places/resolver.py`
- Test: `backend/tests/unit/twin/test_resolver.py` (uses the Task 2 fixtures plus a test aliases file)

**Interfaces:**
- Consumes: `load_lgd` output, `normalize_name`.
- Produces:
  - `@dataclass PlaceMatch: place_id: str; name: str; level: str; state_code: str | None; score: float; method: Literal["exact","alias","fuzzy"]`
  - `@dataclass Resolution: matches: list[PlaceMatch]; ambiguous: bool`
  - `class PlaceResolver: __init__(places: pd.DataFrame, aliases: pd.DataFrame)`
    - `resolve(text: str, level: str | None = None, state_code: str | None = None, limit: int = 5) -> Resolution`
    - Order: exact on `name_norm` → alias (respecting `state_code` when the alias has one) → fuzzy with `rapidfuzz.process.extract(scorer=fuzz.WRatio)`, keeping scores ≥ 90.
    - `ambiguous` is True when there's more than one match at the top score and they're in different states.
    - Exact and alias matches score 100.
  - `load_aliases(path: Path) -> pd.DataFrame`

- [ ] **Step 1: Write the failing tests**

```python
def test_exact(resolver):
    r = resolver.resolve("Gaya")
    assert [m.name for m in r.matches][:1] == ["Gaya"] and r.ambiguous is False

def test_alias_old_name(resolver):
    r = resolver.resolve("Bombay", level="district")
    assert r.matches[0].name == "Mumbai" and r.matches[0].method == "alias"

def test_ambiguous_name_returns_all_candidates(resolver):
    r = resolver.resolve("Aurangabad", level="district")
    assert r.ambiguous is True
    assert {m.state_code for m in r.matches} == {"10", "27"}

def test_state_hint_disambiguates(resolver):
    r = resolver.resolve("Aurangabad", level="district", state_code="10")
    assert r.ambiguous is False and r.matches[0].state_code == "10"

def test_fuzzy_typo(resolver):
    m = resolver.resolve("Patnaa").matches[0]
    assert m.name == "Patna" and m.method == "fuzzy" and m.score >= 90

def test_unknown_returns_empty(resolver):
    r = resolver.resolve("Atlantis")
    assert r.matches == [] and r.ambiguous is False
```

The Bihar fixture's Aurangabad keeps the name "Aurangabad". The Maharashtra one is named "Chhatrapati Sambhajinagar" with the alias "aurangabad" (27), so both candidates surface.

- [ ] **Step 2: Run the tests and confirm they fail.** Run: `pytest tests/unit/twin/test_resolver.py -v`.
- [ ] **Step 3: Implement `resolver.py`** as specified.
- [ ] **Step 4: Run the tests and confirm they pass.** Expected: 6 passed.
- [ ] **Step 5: Commit.** `git commit -m "feat(twin): resolve place names with aliases, fuzzy match and ambiguity"`

---

### Task 4: SoI boundaries (district, state, national), clipped and simplified

**Files:**
- Create: `backend/twin/places/boundaries.py`
- Create fixtures:
  - `backend/tests/fixtures/twin/soi_outline.geojson`: a 10×10° square
  - `backend/tests/fixtures/twin/soi_districts.geojson`: square polygons for the Task 2 districts. One pokes outside the outline, and one has a name spelled differently from LGD ("Gaya Dist.").
- Test: `backend/tests/unit/twin/test_boundaries.py`

**Interfaces:**
- Consumes: `PlaceResolver`, places DataFrame.
- Produces:
  - `SOI_DISTRICT_COLUMNS: dict[str, str]` maps shapefile attribute names to `district_name` and `state_name`. If the real file differs, change only this dict.
  - `build_district_boundaries(districts_path: Path, outline_path: Path, places: pd.DataFrame, resolver: PlaceResolver) -> tuple[gpd.GeoDataFrame, list[str]]`
    - Returns a GeoDataFrame with `place_id`, `geometry` (EPSG:4326) and a list of unmatched source names.
    - Matching: resolve `state_name` to a state, then resolve `district_name` with `level="district"` and that `state_code`.
    - Geometry is clipped to the outline.
  - `dissolve_levels(districts: gpd.GeoDataFrame, places: pd.DataFrame) -> dict[str, gpd.GeoDataFrame]` returns keys `"district"`, `"state"` and `"country"`. States and the country are dissolved from districts.
  - `write_boundaries(levels: dict[str, gpd.GeoDataFrame], out_dir: Path, simplify_m: dict[str, float] = {"district": 300, "state": 800, "country": 1500}) -> None`
    - Writes `boundaries_<level>.parquet` (GeoParquet, full detail).
    - Writes `boundaries_<level>.geojson`, simplified using the tolerance in metres (in EPSG:7755, preserving topology), with properties `place_id` and `name`.

- [ ] **Step 1: Write the failing tests**

```python
def test_every_lgd_district_gets_geometry_and_misspelling_matches(fx, places, resolver):
    gdf, unmatched = build_district_boundaries(fx/"soi_districts.geojson", fx/"soi_outline.geojson", places, resolver)
    assert unmatched == []
    assert set(gdf.place_id) == set(places[places.level == "district"].place_id)

def test_clip_removes_area_outside_outline(fx, places, resolver):
    gdf, _ = build_district_boundaries(fx/"soi_districts.geojson", fx/"soi_outline.geojson", places, resolver)
    outline = gpd.read_file(fx/"soi_outline.geojson").union_all()
    assert gdf.geometry.apply(lambda g: g.difference(outline).area).max() < 1e-9

def test_dissolve_and_write(tmp_path, fx, places, resolver):
    gdf, _ = build_district_boundaries(fx/"soi_districts.geojson", fx/"soi_outline.geojson", places, resolver)
    levels = dissolve_levels(gdf, places)
    assert len(levels["country"]) == 1
    write_boundaries(levels, tmp_path)
    fc = json.loads((tmp_path/"boundaries_district.geojson").read_text())
    assert {"place_id", "name"} <= set(fc["features"][0]["properties"])
```

`places` and `resolver` are conftest fixtures built from the Task 2/3 fixtures.

- [ ] **Step 2: Run the tests and confirm they fail.**
- [ ] **Step 3: Implement `boundaries.py`.**
- [ ] **Step 4: Run the tests and confirm they pass.** Expected: 3 passed.
- [ ] **Step 5: Commit.** `git commit -m "feat(twin): build SoI-clipped district, state and national boundaries"`

---

### Task 5: Census 2011 → current district crosswalk

**Files:**
- Create: `backend/twin/places/crosswalk.py`
- Create fixture: `backend/tests/fixtures/twin/census2011_districts.geojson`. Three 2011 districts, laid over the Task 4 current-district squares:
  - A maps 1:1 onto **X = Patna**
  - B was split 60/40 by area into **Y = Gaya** and **Z = Aurangabad (Bihar)**
  - C maps onto Mumbai, with a 0.2% sliver into Chhatrapati Sambhajinagar
  - The post-2011 district from Task 2 overlaps no 2011 district. It's the "no Census data" case.

  `conftest.py` exposes the constants `X_ID`, `Y_ID`, `Z_ID` and `NEW_DISTRICT_ID` (the fixture LGD codes). The tests below write `"district:X"`, `"district:Y"` and so on as shorthand for them.
- Test: `backend/tests/unit/twin/test_crosswalk.py`

**Interfaces:**
- Produces:
  - `build_crosswalk(old: gpd.GeoDataFrame, new: gpd.GeoDataFrame, pop_weights: pd.DataFrame | None = None, sliver: float = 0.005) -> pd.DataFrame`
    - Inputs: `old` and `new` both have `place_id` and `geometry`.
    - Returns columns `old_id`, `new_id`, `area_weight`, `pop_weight` (NaN when `pop_weights` is None).
    - Overlap is computed in EPSG:6933 (equal area).
    - Pieces with `area_weight < sliver` are dropped, then weights are renormalised so each `old_id` sums to 1.
  - `apply_crosswalk(obs: pd.DataFrame, xwalk: pd.DataFrame, method: Literal["sum","mean"], weight: Literal["area","pop"] = "area") -> pd.DataFrame`
    - `obs` follows the shared schema, with `place_id`s from the old geography.
    - Returns observations keyed by `new_id`.
    - `sum`: value × weight, summed per new district.
    - `mean`: weighted mean using the weights of the pieces that make up each new district.
    - Null values stay null, never 0.

- [ ] **Step 1: Write the failing tests**

```python
def test_weights_sum_to_one_and_drop_slivers(old, new):
    x = build_crosswalk(old, new)
    assert x.groupby("old_id").area_weight.sum().round(9).eq(1).all()
    assert not ((x.old_id == "census2011_district:C") & (x.area_weight < 0.005)).any()

def test_split_district_conserves_total(old, new):
    x = build_crosswalk(old, new)
    obs = obs_frame({"census2011_district:A": 100, "census2011_district:B": 1000, "census2011_district:C": 10})
    out = apply_crosswalk(obs, x, "sum")
    assert out.value.sum() == pytest.approx(1110)
    assert out.set_index("place_id").value["district:Y"] == pytest.approx(600, rel=1e-3)

def test_null_stays_null(old, new):
    out = apply_crosswalk(obs_frame({"census2011_district:A": None}), build_crosswalk(old, new), "sum")
    assert out.set_index("place_id").value.isna()["district:X"]
```

- [ ] **Step 2: Run the tests and confirm they fail.**
- [ ] **Step 3: Implement `crosswalk.py`.**
- [ ] **Step 4: Run the tests and confirm they pass.** Expected: 3 passed.
- [ ] **Step 5: Commit.** `git commit -m "feat(twin): area-weighted 2011-to-current district crosswalk"`

---

### Task 6: H3 linking

**Files:**
- Create: `backend/twin/places/h3link.py`
- Test: `backend/tests/unit/twin/test_h3link.py` (fixture districts plus an in-test 2 km square "island" polygon)

**Interfaces:**
- Produces: `build_h3_index(districts: gpd.GeoDataFrame, resolutions: tuple[int, ...] = (5, 7)) -> pd.DataFrame`
  - Returns columns `cell`, `res`, `place_id`.
  - Cells come from `h3.h3shape_to_cells` (centre-in-polygon).
  - Any district with zero cells at a resolution gets the cell containing `geometry.representative_point()`.
  - Each `(cell, res)` appears at most once.
  - When a fallback cell is already owned by another district, ownership moves to the tiny district if the owner keeps at least one other cell. Otherwise the tiny district takes the first unowned cell in `h3.grid_ring(cell, 1)`.

- [ ] **Step 1: Write the failing tests**

```python
def test_every_district_has_cells_at_each_res(districts):
    idx = build_h3_index(districts)
    for res in (5, 7):
        assert set(idx[idx.res == res].place_id) == set(districts.place_id)

def test_tiny_island_district_gets_a_cell(districts_with_island):
    idx = build_h3_index(districts_with_island, (5,))
    assert (idx.place_id == "district:island").sum() == 1

def test_cells_unique_per_res(districts):
    idx = build_h3_index(districts)
    assert not idx.duplicated(["cell", "res"]).any()
```

- [ ] **Step 2: Run the tests and confirm they fail.**
- [ ] **Step 3: Implement `h3link.py`.**
- [ ] **Step 4: Run the tests and confirm they pass.** Expected: 3 passed.
- [ ] **Step 5: Commit.** `git commit -m "feat(twin): link districts to H3 cells at res 5 and 7"`

---

### Task 7: Pipeline framework, Parquet store, catalogue and source registry entries

**Files:**
- Create: `backend/twin/pipeline/__init__.py`, `backend/twin/pipeline/base.py`, `backend/twin/store/parquet_store.py`, `backend/twin/store/catalog.py`
- Modify: `backend/app/data_registry.py`
  - Add `SourceDefinition`s `lgd`, `soi-boundaries` and `census2011-pca-district`, with real URLs and licences:
    - LGD: `https://lgdirectory.gov.in/`, "Government Open Data License - India"
    - SoI: `https://onlinemaps.surveyofindia.gov.in/`, "Survey of India terms"
    - Census: reuse the `census-pca` URL
  - Add `census2011-district-boundaries`: DataMeet, `https://github.com/datameet/maps`, "CC BY 2.5 IN", `confidence_class="open_proxy"`, used only for the crosswalk and **never drawn**.
  - `viirs` already exists.
- Test: `backend/tests/unit/twin/test_pipeline.py`, `backend/tests/unit/twin/test_catalog.py`

**Interfaces:**
- Consumes: `TwinPaths`, `validate_observations`, `SOURCE_REGISTRY`.
- Produces:
  - `@dataclass Indicator: id: str; name: str; description: str; unit: str; domains: tuple[str, ...]; source_id: str`
  - `@dataclass ValidationReport: ok: bool; problems: list[str]; stats: dict[str, float]`
  - `@dataclass PipelineContext: paths: TwinPaths; places: pd.DataFrame; boundaries: dict[str, gpd.GeoDataFrame]; crosswalk: pd.DataFrame | None; known_sources: set[str] = field(default_factory=set)`
  - `class SourceAdapter(Protocol)`:
    - attributes `source_id: str`, `indicators: list[Indicator]`, `transform_version: str`
    - `input_files(manual_dir: Path) -> list[Path]`
    - `observed_period(files: list[Path]) -> str`
    - `parse(files: list[Path], ctx: PipelineContext) -> pd.DataFrame` returns schema rows
    - `validate(obs: pd.DataFrame, ctx: PipelineContext) -> ValidationReport`
  - `@dataclass PublishResult: dataset_version: str; published: bool; reused: bool; report: ValidationReport`
  - `run_pipeline(adapter: SourceAdapter, ctx: PipelineContext) -> PublishResult`. Steps:
    1. Raise `KeyError` if `source_id` isn't in `SOURCE_REGISTRY`.
    2. Compute the SHA-256 over the sorted input file bytes. `dataset_version = f"{source_id}@{period}#{sha[:12]}"`.
    3. If that version is already published, return `reused=True` without re-parsing.
    4. Copy inputs to `raw/<source_id>/<sha[:12]>/` with `manifest.json` (file names, sizes, sha, fetched_at, transform_version).
    5. Parse, then run `validate_observations` plus `adapter.validate`. If either fails, return `published=False` and don't write `published/`.
    6. Otherwise write `observations.parquet` + `report.json`, upsert the adapter's indicators into the catalogue, and set `CURRENT.json[source_id] = dataset_version`. Older versions stay on disk.
  - `parquet_store`:
    - `write_dataset(paths, source_id, dataset_version, obs) -> Path`
    - `is_published(paths, source_id, dataset_version) -> bool`
    - `read_current(paths) -> dict[str, str]`
    - `set_current(paths, source_id, dataset_version) -> None`
    - `query_observations(paths, place_ids: list[str] | None = None, indicators: list[str] | None = None) -> pd.DataFrame`: DuckDB over the **current** version of every source. Adds a `source_name` column joined from `SOURCE_REGISTRY` (passed in as a `dict[str, str]` argument `source_names` so `twin` doesn't import `app`).
  - `catalog`:
    - `upsert_indicators(paths, indicators: list[Indicator]) -> None`
    - `list_indicators(paths) -> list[Indicator]`
    - `search_indicators(paths, query: str, limit: int = 10) -> list[Indicator]`: rapidfuzz `WRatio` over name + description. M2 replaces this with embeddings.

  - `search_indicators` keeps only results with WRatio ≥ 60.

  Note: `run_pipeline` checks sources against `ctx.known_sources`. That keeps `twin` free of `app` imports. `scripts/twin_build.py` and the API fill it from `SOURCE_REGISTRY`.

- [ ] **Step 1: Write the failing tests** (using a `DummyAdapter` in the test file that emits two rows from one fixture CSV)

```python
def test_unknown_source_rejected(ctx):
    with pytest.raises(KeyError):
        run_pipeline(DummyAdapter(source_id="nope"), ctx)

def test_publish_writes_raw_manifest_and_current(ctx):
    r = run_pipeline(DummyAdapter(), ctx)
    assert r.published and not r.reused
    assert any((ctx.paths.raw / "dummy").glob("*/manifest.json"))
    assert read_current(ctx.paths)["dummy"] == r.dataset_version

def test_failed_validation_does_not_publish(ctx):
    r = run_pipeline(DummyAdapter(fail=True), ctx)
    assert r.published is False and "dummy" not in read_current(ctx.paths)

def test_rerun_same_input_is_idempotent(ctx):
    a = run_pipeline(DummyAdapter(), ctx); b = run_pipeline(DummyAdapter(), ctx)
    assert b.reused and a.dataset_version == b.dataset_version

def test_changed_input_creates_new_version(ctx):
    a = run_pipeline(DummyAdapter(), ctx); ctx_file_append(ctx, "x"); b = run_pipeline(DummyAdapter(), ctx)
    assert a.dataset_version != b.dataset_version
    assert is_published(ctx.paths, "dummy", a.dataset_version)  # old kept
    assert read_current(ctx.paths)["dummy"] == b.dataset_version

def test_catalog_search(tmp_paths):
    upsert_indicators(tmp_paths, [Indicator("population_total", "Total population", "All persons", "persons", ("population",), "census2011-pca-district")])
    assert search_indicators(tmp_paths, "population")[0].id == "population_total"
    assert search_indicators(tmp_paths, "zzzz unrelated") == []   # WRatio cutoff 60
```

The test registers `"dummy"` in `ctx.known_sources`. `test_unknown_source_rejected` uses an id outside it.

- [ ] **Step 2: Run the tests and confirm they fail.** Run: `pytest tests/unit/twin/test_pipeline.py tests/unit/twin/test_catalog.py -v`.
- [ ] **Step 3: Implement `parquet_store.py`, `catalog.py`, `base.py` and the registry entries.**
- [ ] **Step 4: Run the tests and confirm they pass.** Also run `pytest tests/unit/test_data_registry.py` (it must still pass).
- [ ] **Step 5: Commit.** `git commit -m "feat(twin): versioned pipeline framework, parquet store and indicator catalogue"`

---

### Task 8: Backbone build orchestration

**Files:**
- Create: `backend/twin/places/build.py`
- Test: `backend/tests/unit/twin/test_build.py`

**Interfaces:**
- Consumes: Tasks 2–6.
- Produces:
  - `@dataclass BackboneInputs: lgd_states: Path; lgd_districts: Path; soi_districts: Path; soi_outline: Path; census2011_districts: Path; aliases: Path`
  - `build_backbone(inputs: BackboneInputs, paths: TwinPaths, boundary_version: str) -> BackboneReport`. It:
    1. Loads LGD and the resolver.
    2. Builds the boundaries.
    3. Builds the crosswalk. 2011 place ids are `census2011_district:<state2><dist3>`, taken from the DataMeet attributes via a `CENSUS2011_COLUMNS` mapping dict.
    4. Builds the H3 index.
    5. Writes `places.parquet`, `aliases.parquet`, boundaries (Task 4), `crosswalk_census2011.parquet` and `h3_index.parquet` to `paths.places_dir(boundary_version)`.
    6. Sets `CURRENT.json["places"] = boundary_version`.
  - `@dataclass BackboneReport: districts: int; states: int; unmatched_boundaries: list[str]; districts_without_census2011_link: int`
  - `load_backbone(paths: TwinPaths, known_sources: set[str] | None = None) -> PipelineContext`: reads the current places version.

- [ ] **Step 1: Write the failing test**

```python
def test_build_backbone_end_to_end(fx, tmp_paths):
    rep = build_backbone(fixture_inputs(fx), tmp_paths, "lgd-test")
    assert rep.unmatched_boundaries == [] and rep.districts == 7
    ctx = load_backbone(tmp_paths)
    assert {"district", "state", "country"} <= set(ctx.boundaries)
    assert ctx.crosswalk is not None and len(ctx.crosswalk) > 0
```

- [ ] **Step 2: Run the test and confirm it fails.**
- [ ] **Step 3: Implement `build.py`.**
- [ ] **Step 4: Run the test and confirm it passes.**
- [ ] **Step 5: Commit.** `git commit -m "feat(twin): orchestrate backbone build into versioned places directory"`

---

### Task 9: Census 2011 PCA district adapter

**Files:**
- Create: `backend/twin/pipeline/census2011.py`
- Create fixture: `backend/tests/fixtures/twin/pca_district.csv`, with the real PCA header subset `State,District,Level,TRU,Name,TOT_P,TOT_M,TOT_F,P_LIT,TOT_WORK_P` and rows for fixture districts A, B and C (TRU = Total, Rural and Urban rows; only Total is used) plus an `INDIA` row.
- Test: `backend/tests/unit/twin/test_census2011.py`

**Interfaces:**
- Consumes: `SourceAdapter`, `apply_crosswalk`.
- Produces: `Census2011Adapter(SourceAdapter)`
  - `source_id = "census2011-pca-district"`
  - `transform_version = "census2011-v1"`
  - `input_files` = `manual/census2011/pca_district*.csv`
  - `observed_period = "2011"`
  - Indicators (all `sum`, unit `persons`, trust_label `fact`):

    | Indicator | Column |
    |---|---|
    | `population_total` | `TOT_P` |
    | `population_male` | `TOT_M` |
    | `population_female` | `TOT_F` |
    | `literates_total` | `P_LIT` |
    | `workers_total` | `TOT_WORK_P` |

  - It filters `Level == "DISTRICT"` and `TRU == "Total"`, builds `census2011_district:<State:02d><District:03d>` ids, applies the crosswalk (area weights in M1), and sets `trust_label` to `"fact"` for 1:1 mappings and `"pattern"` for apportioned pieces (where a new district received <100% from a single old district).
  - `validate`:
    - The national `population_total` sum must be within 0.01% of the `INDIA` row's `TOT_P`. For real data that's **1,210,854,977**.
    - All current districts with a non-null `census2011_code` or a crosswalk link get a value. Other districts are listed in `stats["districts_without_value"]` (allowed, reported).

- [ ] **Step 1: Write the failing tests**

```python
def test_national_population_conserved(ctx_backbone):
    obs = Census2011Adapter().parse(Census2011Adapter().input_files(ctx_backbone.paths.manual), ctx_backbone)
    tot = obs[obs.indicator == "population_total"].value.sum()
    assert tot == pytest.approx(INDIA_ROW_TOTAL_IN_FIXTURE, rel=1e-4)

def test_split_district_marked_pattern(ctx_backbone):
    obs = ...  # as above
    y = obs[(obs.place_id == "district:Y") & (obs.indicator == "population_total")].iloc[0]
    assert y.trust_label == "pattern"

def test_publishes_through_pipeline(ctx_backbone):
    assert run_pipeline(Census2011Adapter(), ctx_backbone).published
```

`ctx_backbone` builds the backbone from the fixtures and copies `pca_district.csv` to `manual/census2011/`.

- [ ] **Step 2: Run the tests and confirm they fail.**
- [ ] **Step 3: Implement the adapter.**
- [ ] **Step 4: Run the tests and confirm they pass.** Expected: 3 passed.
- [ ] **Step 5: Commit.** `git commit -m "feat(twin): Census 2011 PCA adapter apportioned to current districts"`

---

### Task 10: VIIRS annual nightlights adapter

**Files:**
- Create: `backend/twin/pipeline/viirs.py`
- Test: `backend/tests/unit/twin/test_viirs.py`. The test writes a 20×20 GeoTIFF over the fixture extent with rasterio: constant 1.0, one NaN pixel, one negative pixel.

**Interfaces:**
- Produces: `ViirsAdapter(SourceAdapter)`
  - `source_id = "viirs"`
  - `transform_version = "viirs-zonal-v1"`
  - `input_files` = `manual/viirs/VNL_*_<year>_*average_masked*.tif`. The year is parsed from the filename and becomes `observed_period`.
  - Indicator `nightlights_radiance_sum`: unit `nW/cm²/sr·px`, domain `economy`, trust `fact`. Its description must state "a proxy for economic activity, not GDP".
  - Zonal sum per district uses `rasterio.mask.mask(crop=True)` over the full-detail district geometry. Negative values and NaN are treated as 0 within the sum.
  - `validate`: every district has a non-null value ≥ 0, and `stats["total"]` > 0.

- [ ] **Step 1: Write the failing tests**

```python
def test_zonal_sum_per_district(ctx_backbone, tiff):
    obs = ViirsAdapter().parse([tiff], ctx_backbone)
    assert set(obs.place_id) == set(ctx_backbone.boundaries["district"].place_id)
    assert (obs.value >= 0).all() and obs.period.eq("2023").all()

def test_negative_and_nan_pixels_ignored(ctx_backbone, tiff):
    obs = ViirsAdapter().parse([tiff], ctx_backbone)
    assert obs.value.sum() == pytest.approx(EXPECTED_SUM_FROM_FIXTURE)
```

`tiff` is named `VNL_v2_npp_2023_global_vcmslcfg_c202402081600.average_masked.dat.tif`.

- [ ] **Step 2: Run the tests and confirm they fail.**
- [ ] **Step 3: Implement the adapter.**
- [ ] **Step 4: Run the tests and confirm they pass.** Expected: 2 passed.
- [ ] **Step 5: Commit.** `git commit -m "feat(twin): VIIRS nightlights zonal-sum adapter"`

---

### Task 11: Build CLI, manual-download guide and Postgres sync

**Files:**
- Create: `backend/scripts/twin_build.py`, `data/twin/manual/README.md`, `docs/twin/DATA_SOURCES.md`
- Create: `backend/twin/store/pg_sync.py`, `supabase/migrations/009_twin_places.sql`
- Test: `backend/tests/unit/twin/test_cli.py`, `backend/tests/unit/twin/test_pg_sync.py`

**Interfaces:**
- Produces:
  - `python scripts/twin_build.py check` lists every expected manual file with ✓ or ✗ and exits 1 if any required file is missing.
  - `python scripts/twin_build.py build --boundary-version lgd-YYYYMMDD` runs `build_backbone`, then each adapter in the order Census and VIIRS. It prints `BackboneReport` and each `PublishResult` as JSON lines. It exits non-zero if any adapter fails validation.
  - `EXPECTED_MANUAL_FILES: dict[str, str]` maps each relative path (glob) to its download instructions. It's the single source for both `check` and `README.md`. Required paths:
    - `lgd/states.csv`
    - `lgd/districts.csv`
    - `soi/district_boundaries.*` (shp/geojson)
    - `soi/india_outline.*`
    - `census2011/district_boundaries.*`
    - `census2011/pca_district*.csv`
    - `viirs/VNL_*average_masked*.tif`
  - `sync_to_postgres(paths: TwinPaths, dsn: str) -> dict[str, int]` upserts places (with PostGIS geometry from the full-detail boundaries), indicators and `dataset_versions` rows. It returns row counts per table. When `dsn` is empty it returns `{}` and logs "postgres sync skipped".
  - Migration `009_twin_places.sql`:
    - `CREATE EXTENSION IF NOT EXISTS postgis;`
    - `twin_places(place_id text primary key, level text not null, lgd_code text, name text not null, parent_id text, state_code text, boundary_version text not null, geom geometry(MultiPolygon,4326))`
    - `twin_indicators(id text primary key, name text, description text, unit text, domains text[], source_id text)`
    - a GIST index on `geom`

- [ ] **Step 1: Write the failing tests**

```python
def test_check_reports_missing_files(tmp_paths, capsys):
    assert main(["check"], paths=tmp_paths) == 1
    assert "lgd/districts.csv" in capsys.readouterr().out

def test_build_runs_on_fixtures(fixture_manual_paths):
    assert main(["build", "--boundary-version", "lgd-test"], paths=fixture_manual_paths) == 0

def test_pg_sync_skips_without_dsn(tmp_paths):
    assert sync_to_postgres(tmp_paths, "") == {}
```

`fixture_manual_paths` lays the Task 2–10 fixtures out in the `manual/` structure, including generating the TIFF.

- [ ] **Step 2: Run the tests and confirm they fail.**
- [ ] **Step 3: Implement the CLI (with `main(argv, paths=None) -> int`), the README generated from `EXPECTED_MANUAL_FILES`, `DATA_SOURCES.md`, `pg_sync.py` (psycopg2, `execute_values`) and the migration.**

  `DATA_SOURCES.md` lists each source with its registry id, URL, licence, what it feeds, and the note that the DataMeet 2011 boundaries are only used for the crosswalk and never drawn.

- [ ] **Step 4: Run the tests and confirm they pass.** Expected: 3 passed.
- [ ] **Step 5: Commit.** `git commit -m "feat(twin): build CLI, manual data guide and optional Postgres sync"`

---

### Task 12: Twin API

**Files:**
- Create: `backend/app/routes/twin.py`
- Modify: `backend/app/main.py` (add `app.include_router(twin_router, prefix="/api/twin", tags=["twin"])`)
- Test: `backend/tests/integration/test_twin_api.py`. It builds fixtures into a tmp `TWIN_DATA_DIR` via `twin_build.main` and overrides the `get_twin_paths` dependency.

**Interfaces:**
- Consumes: `load_backbone`, `PlaceResolver`, `query_observations`, `list_indicators`, `SOURCE_REGISTRY`.
- Produces (all wrapped in the envelope):

  | Endpoint | Returns |
  |---|---|
  | `GET /api/twin/places/resolve?q=&level=&state=` | `data: {matches: PlaceMatch[], ambiguous: bool}` |
  | `GET /api/twin/places/{place_id}` | `data: {place_id, name, level, parent: {place_id, name} | null, state: {place_id, name} | null}`; 404 envelope if unknown |
  | `GET /api/twin/places/{place_id}/observations` | see below |
  | `GET /api/twin/boundaries/{level}` | level ∈ `country`, `state`, `district`; raw simplified GeoJSON FeatureCollection, **not enveloped**; `Cache-Control: public, max-age=86400`; 404 for other levels |
  | `GET /api/twin/indicators` | `data: Indicator[]` |

  The observations endpoint returns:
  - `data: [{indicator, name, unit, period, value, trust_label, receipt: {source_id, source_name, dataset_version, license, url}}]`
  - one entry per catalogued indicator; when a place has no row for an indicator, `value: null` and `receipt` is that indicator's source with `dataset_version` from `CURRENT.json`
  - `meta: {places_version}`

  The boundaries endpoint is not enveloped because GeoJSON is a file-like asset that the map loads directly. This is a deliberate exception and should be noted in the route docstring.

  Dependencies `get_twin_paths()` and `get_twin_context()` are cached per `CURRENT.json` mtime.

- [ ] **Step 1: Write the failing tests**

```python
def test_resolve_ambiguous(client):
    body = client.get("/api/twin/places/resolve", params={"q": "Aurangabad", "level": "district"}).json()
    assert body["success"] and body["data"]["ambiguous"] is True

def test_observations_have_receipts(client, gaya_id):
    rows = client.get(f"/api/twin/places/{gaya_id}/observations").json()["data"]
    pop = next(r for r in rows if r["indicator"] == "population_total")
    assert pop["value"] > 0 and pop["receipt"]["source_id"] == "census2011-pca-district"
    assert pop["receipt"]["license"]

def test_missing_value_is_null_not_zero(client, district_without_census_id):
    rows = client.get(f"/api/twin/places/{district_without_census_id}/observations").json()["data"]
    pop = next(r for r in rows if r["indicator"] == "population_total")
    assert pop["value"] is None

def test_boundaries_geojson(client):
    r = client.get("/api/twin/boundaries/district")
    assert r.status_code == 200 and r.json()["type"] == "FeatureCollection"
    assert client.get("/api/twin/boundaries/ward").status_code == 404

def test_unknown_place_404_envelope(client):
    r = client.get("/api/twin/places/district:99999")
    assert r.status_code == 404 and r.json()["success"] is False
```

In the fixture, the new district (null census code and no crosswalk overlap) is `district_without_census_id`.

- [ ] **Step 2: Run the tests and confirm they fail.** Run: `pytest tests/integration/test_twin_api.py -v`.
- [ ] **Step 3: Implement `routes/twin.py` and register it.**
- [ ] **Step 4: Run the tests and confirm they pass.** Expected: 5 passed.
- [ ] **Step 5: Commit.** `git commit -m "feat(api): add /api/twin places, observations, boundaries and indicators"`

---

### Task 13: Frontend India map, search and place card

**Files:**
- Create: `frontend/src/types/twin.ts`, `frontend/src/lib/twinApi.ts`, `frontend/src/store/twinStore.ts`
- Create: `frontend/src/components/twin/IndiaMap.tsx`, `PlaceSearch.tsx`, `PlaceCard.tsx`
- Create tests: `PlaceCard.test.tsx`, `PlaceSearch.test.tsx`, `frontend/src/store/twinStore.test.ts`
- Modify: `frontend/src/app/page.tsx` (replaced: full-screen `IndiaMap`, `PlaceSearch` top-left, `PlaceCard` right drawer)

**Interfaces:**
- Consumes: the Task 12 endpoints. The base URL is `process.env.NEXT_PUBLIC_API_URL` (already used by the app).
- Produces:
  - **types:**
    - `PlaceMatch`
    - `Resolution`
    - `Receipt { sourceId; sourceName; datasetVersion; license; url }`
    - `Observation { indicator; name; unit; period; value: number | null; trustLabel: 'fact'|'pattern'|'projection'; receipt: Receipt }`

    `twinApi` maps snake_case to camelCase.
  - **twinApi:**
    - `resolvePlace(q, opts?) => Promise<Resolution>`
    - `getPlace(id)`
    - `getObservations(id) => Promise<Observation[]>`
    - `boundariesUrl(level) => string`
  - **twinStore (Zustand):**
    - `selectedPlaceId: string | null`
    - `observations: Observation[]`
    - `loading: boolean`
    - `error: string | null`
    - `selectPlace(id: string) => Promise<void>`
    - `clear() => void`
  - **IndiaMap:**
    - deck.gl `DeckGL` with **no basemap**, and a background colour token `--map-bg: #05070d`
    - three `GeoJsonLayer`s from `boundariesUrl`:
      - district (pickable; thin `#2c4a6e` lines; hover highlight; click → `selectPlace`)
      - state (thicker lines, not pickable)
      - country (outline)
    - initial view: `{longitude: 82.8, latitude: 22.5, zoom: 3.8}`
    - when a place is selected, the selected district is filled with `#ff9f1c55` and the view flies to its bounds
  - **PlaceSearch:**
    - input → debounced 250 ms `resolvePlace`
    - shows a candidate list with state names
    - when `ambiguous` it shows the heading "Which one?" and never auto-selects
    - selecting calls `selectPlace`
  - **PlaceCard:**
    - the place name and its state
    - one row per observation: name, formatted value (`Intl.NumberFormat('en-IN')`), unit, period, and a trust chip (`Fact`, `Pattern`, `Projection`)
    - when `value === null` it shows **"No data"**
    - each row expands a receipt: source name (linked to url), dataset version, licence
    - footer: "Census 2011 values for districts created after 2011 are apportioned by area. They're marked Pattern."

- [ ] **Step 1: Write the failing tests**

```tsx
it('PlaceCard shows No data for null', () => {
  render(<PlaceCard name="X" stateName="Y" observations={[obs({ value: null })]} />);
  expect(screen.getByText('No data')).toBeInTheDocument();
  expect(screen.queryByText('0')).not.toBeInTheDocument();
});
it('PlaceCard formats Indian numbering and shows trust chip and receipt', async () => {
  render(<PlaceCard name="Gaya" stateName="Bihar" observations={[obs({ value: 4391418, trustLabel: 'fact' })]} />);
  expect(screen.getByText('43,91,418')).toBeInTheDocument();
  expect(screen.getByText('Fact')).toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: /source/i }));
  expect(screen.getByText(/census2011-pca-district@2011/)).toBeInTheDocument();
});
it('PlaceSearch lists all candidates and does not auto-select when ambiguous', async () => {
  mockResolve({ ambiguous: true, matches: [m('Aurangabad', 'Bihar'), m('Chhatrapati Sambhajinagar', 'Maharashtra')] });
  render(<PlaceSearch />); await userEvent.type(screen.getByRole('searchbox'), 'Aurangabad');
  expect(await screen.findByText('Which one?')).toBeInTheDocument();
  expect(useTwinStore.getState().selectedPlaceId).toBeNull();
});
it('twinStore.selectPlace loads observations and records errors', async () => { /* mock getObservations ok then reject */ });
```

- [ ] **Step 2: Run the tests and confirm they fail.** Run: `cd frontend && npx jest src/components/twin src/store/twinStore.test.ts`.
- [ ] **Step 3: Implement the types, API, store and components, and replace `page.tsx`.**
- [ ] **Step 4: Run the tests and confirm they pass.** Then run `npm run lint && npm run type-check`. Expected: the new tests pass and lint and type-check are clean. Old tests that break because `page.tsx` changed get handled in Task 14.
- [ ] **Step 5: Commit.** `git commit -m "feat(frontend): India map with district search and sourced place card"`

---

### Task 14: Retire the legacy city simulator

**Files:**
- Delete (backend):
  - `engine/primary_loop.py`, `engine/secondary_loop.py`, `engine/tertiary_loop.py`, `engine/runner.py`, `engine/serializer.py`, `engine/overlay.py`
  - `app/ws/simulation.py`, `app/routes/simulations.py`
  - their tests: `test_primary_loop.py`, `test_secondary_loop.py`, `test_tertiary_loop.py`, `test_serializer*.py`, `tests/integration/test_ws_simulation.py`, and the simulation cases in `test_rest_endpoints.py`
- Delete (frontend):
  - `components/controls/*`, `components/dashboard/*`, `components/map/*`
  - `hooks/useWebSocket*`, `hooks/useKeyboardShortcuts*`
  - `lib/ws*`, `lib/colorScale*`, `lib/mapConfig.ts`
  - `store/simulationStore*`, `types/simulation.ts`
- Modify: `backend/app/main.py` (remove the simulation router and websocket)

**Rule for anything not listed:** after deleting, run `grep` for imports of each deleted module. A file that imports a deleted module is either:
- **retired code itself:** delete it and its tests, or
- **a keeper** (`engine/agent/`, `app/ws/agent.py`, `app/rag/`, `nl_engine/`, `engine/config.py`, `engine/models.py`, `app/data_registry.py`, `app/realtime*`, `app/db.py`): remove only the dead import or the function that uses it.

Keepers are reworked in M2, not here.

**Interfaces:** Afterwards, `/` serves only the twin, and `/api/twin/*`, `/api/health`, `/api/regions*`, `/api/case-studies` and `/ws/agent` still work.

- [ ] **Step 1: Delete the listed files and apply the grep rule.**
- [ ] **Step 2: Run the backend suite.** Run: `cd backend && pytest tests/unit tests/integration -q`. Expected: all pass.
- [ ] **Step 3: Run the frontend checks.** Run: `cd frontend && npm run test && npm run lint && npm run type-check`. Expected: all pass.
- [ ] **Step 4: Update `AGENTS.md`.**
  - Commands: add `python scripts/twin_build.py check|build`.
  - Replace the City Config, Sectors and `overlay_fn` sections with a short "India Twin" section that points to the spec, the `twin/` package and `data/twin/`.
  - Update the test counts to the real numbers.
- [ ] **Step 5: Commit.** `git commit -m "refactor(repo): retire legacy city simulator in favour of India Twin"`

---

### Task 15: M1 acceptance on real data

**Files:**
- Modify: `docs/superpowers/plans/2026-10-18-india-twin-roadmap.md` (mark M1 done, fill in **Learned**)

- [ ] **Step 1: Run the data check.** Run: `cd backend && python scripts/twin_build.py check`.
  - If any file is ✗, stop and give the owner the exact list from `data/twin/manual/README.md`. SoI, VIIRS and LGD downloads need a browser login or a captcha. **Don't fake data.**
- [ ] **Step 2: Build on the real data.** Run: `python scripts/twin_build.py build --boundary-version lgd-<today>`. Expected:
  - `BackboneReport.districts` matches the LGD district count
  - `unmatched_boundaries` is empty. If not, add the missing names to `seed/aliases.csv`, rerun, and commit the aliases.
  - Census `published: true` with national population within 0.01% of 1,210,854,977
  - VIIRS `published: true`
- [ ] **Step 3: Demo check in the browser.** Run the backend and frontend.
  1. Search "Gaya" and select it. The card shows population with a Census receipt, and nightlights with a VIIRS receipt.
  2. Search "Aurangabad". You get "Which one?" with Bihar and Maharashtra.
  3. Click a district created after 2011. It shows Census as Pattern.
  4. The map draws only our layers, with no third-party tiles.

  Take screenshots for the owner.
- [ ] **Step 4: Record what was learned.** Fill the roadmap's **Learned** section: real file quirks, mapping dict changes, alias additions, timings.
- [ ] **Step 5: Commit.** `git commit -m "docs(roadmap): mark M1 backbone complete with learnings"`

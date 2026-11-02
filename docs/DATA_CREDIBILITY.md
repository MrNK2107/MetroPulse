# MetroPulse data credibility

Where every number in MetroPulse comes from, and how much weight it can bear. For what the numbers
cannot tell you, see [`LIMITATIONS.md`](LIMITATIONS.md).

## Three kinds of data

| Kind | Where it appears | Source | Weight it can bear |
|---|---|---|---|
| **Sample model** | Desk: Pulse, Alerts, Siting, Briefing | Seeded synthetic demand built from each city's real anchor points and published population (`frontend/src/lib/pulse/model.ts`) | Illustrative. Shows how the method behaves, not the city's real numbers |
| **Sourced facts** | India Twin district panel | Census 2011, VIIRS night lights, LGD boundaries, each value with a receipt | As good as the source and period named on the receipt |
| **Estimates and proxies** | Planning agent, `/api/regions*`, realtime endpoints | City YAML baselines (GDP, employment, sector weights), news-keyword sentiment | Directional only |

## The desk: honest by construction

- Every desk screen shows a banner saying the city is a sample model, and every briefing repeats
  it in its methodology section.
- The model is deterministic: the same city always gives the same week, so a number in a
  briefing can be reproduced by anyone with the repo.
- No number is written by a language model. The detector and the siting engine are plain
  TypeScript, and each shows its working:
  - **Alerts** carry a rule trace: the baseline rule (median of the same hour in the four
    previous weeks, spread from the MAD), the flag thresholds, how many flagged hex-hours were
    joined, the peak hour, the nearest anchor and the cause rule that fired.
  - **Siting scores** show their formula: 60 × min(1, boardings ÷ reference) + 40 × new-coverage
    share, with the catchment radii and capture rates per mode.
- What changes when a city's own data arrives: the demand field (from AFC taps, survey zones or
  OD matrices) and the existing hubs (from GTFS stations). The detector, siting and briefing stay
  the same.

## The India Twin: receipts and trust labels

Every indicator value served by `/api/twin/places/{id}/observations` carries:

- a **receipt**: source name, licence, dataset version and period;
- a **trust label**: `Fact` when measured directly for that district, `Pattern` when apportioned
  by area from a parent 2011 district because the district was created later.

A missing value is `null`, never 0, and the receipt still names the source. A build writes
versioned Parquet and flips `CURRENT.json` atomically, so the API never mixes two builds. The
build's `report.json` lists districts without a value.

## The agent and the city configs

The 30 city configs in `data/cities/*.yaml` hold population, anchor points and sector weights.
Population and anchors feed the desk. GDP and employment figures are estimates (India publishes
no city-level GDP or unemployment) and are used only by the agent's tools. The agent's
`compare_sectors` tool is a weighted ranking, not a forecast, and its prompts say so.

## Realtime signals (parked)

The backend has six ingestion connectors: Google News RSS, GDELT (fallback), three news-sentiment
proxies (mobility, jobs, land value) and static census. Sentiment tells you what is being reported,
not what is measured. Snapshots record freshness and per-domain quality. Nothing in the current UI
uses them.

## What MetroPulse is and is not

**Is:** a planning desk that demonstrates a working method for demand playback, explained alerts,
station siting and briefings on a sample model of 30 Indian cities, plus a sourced map of
district indicators.

**Is not (yet):** a calibrated ridership forecast, a validated economic model, or a live digital
twin of a city's actual state.

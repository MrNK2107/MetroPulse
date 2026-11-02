# MetroPulse — product brief

> **Test the station before you pour the concrete.**
> MetroPulse is a mobility-intelligence desk for Indian cities. It shows where a city moves,
> hour by hour and hexagon by hexagon. It flags the hours that break pattern and says why in
> plain language. It scores a proposed metro, BRT or feeder stop in seconds, and it turns all
> of that into a briefing a commissioner can read on a phone.

## Name and brand

**MetroPulse** stays. "Metro" points at the buyer (metro rail corporations, metropolitan
authorities) and "Pulse" points at the product (a living, hourly picture, not an annual
report). The visual identity borrows from Indian railway maps and newspaper data desks:

- **Paper and ink.** A warm newsprint ground (`#F4EFE6`) with near-black ink (`#16130F`). It
  reads like a printed planning map, not a neon dashboard.
- **Signal vermilion** (`#D9480F`, the colour of Indian Railways signage) for demand and alerts.
  **Indigo** (`#1E3A8A`) for supply: stations, catchments, proposals.
- **Type.** Fraunces (an editorial serif) for headlines and numbers, IBM Plex Sans for interface
  text, and IBM Plex Mono for timestamps, hex IDs and receipts.
- **Motion only where the data moves:** the 168-hour playback, the catchment ring drawing
  outward, and new alerts sliding into the feed. Nothing else animates.

## Positioning

For **the people who decide where Indian cities build transit**, MetroPulse is the
**demand-first planning desk** that answers "where are people moving, what changed, and what
would a new station do?" in minutes instead of a six-month consultancy cycle. Unlike GIS suites
(powerful, but blank until a specialist fills them) and generic BI dashboards (charts with no
geography), MetroPulse ships with an opinionated city model, explanations in sentences, and an
output format, the briefing, that already matches how Indian authorities make decisions.

## Ideal customer profile

| Segment | Who signs | Job to be done | Why now |
|---|---|---|---|
| **Primary:** metro rail corporations and UMTAs (BMRCL, MMRDA, CMRL, Pune Metro, the 20+ cities with metro under construction or in DPR) | Director (Planning), GM (Business Development) | Pick station sites and feeder routes for the DPR, and defend ridership numbers in front of the board and the MoHUA appraisal | National Transit-Oriented Development policy, Metro Rail Policy 2017 (requires alternatives analysis), PM e-Bus Sewa feeder tenders |
| **Primary:** mobility consultancies that write Comprehensive Mobility Plans and DPRs | Practice lead | Do the first 80% of a demand study (zoning, catchments, option scoring) in days, then spend expert time on calibration | Fixed-fee tenders squeeze margins; whoever does the analysis fastest wins |
| **Secondary:** smart-city SPVs and municipal corporations | CEO, SPV | A weekly picture of city movement with alerts, for the Integrated Command and Control Centre | 100 Smart Cities ICCCs exist but mostly show CCTV walls, not demand |
| **Secondary:** last-mile and logistics operators (e-rickshaw fleets, bike taxis, quick commerce) | Head of Expansion | Choose the next hub or dark store by demand, not by gut feel | Rapid Tier-2 expansion |
| **Tertiary:** real-estate and infrastructure analysts | Research head | Price the "metro premium" on a site before the line is announced | TOD zones raise FAR around stations |

We are building for the **first two**. They feel the pain, hold the budget, and produce the
document (the DPR) where MetroPulse's numbers end up.

## The problem

1. **Siting is slow and opaque.** A metro alignment is decided in a DPR built from a household
   survey that is often five years old. Station-by-station alternatives are rarely compared
   openly, and once a site is chosen the reasoning is hard to revisit.
2. **Cities can't see change.** Authorities learn that a corridor has flipped (a new tech park,
   a flooded underpass, a festival) from newspapers, not from their own data.
3. **Outputs don't travel.** Analysis lives in a GIS file on one consultant's laptop. The
   commissioner needs a two-page brief with a map, a recommendation and the caveats.

## What MetroPulse does (the four headline features)

1. **Pulse: a 168-hour city playback.** Every hexagon (sized like H3 resolution 8, about 0.74 km²) in the
   city has a weekday and a weekend demand profile. Press play to watch a week: the morning
   inbound wave, the evening release, the quiet Sunday. Alerts are pinned on the timeline.
2. **Alerts that explain themselves.** A robust detector compares this week with a trailing
   four-week same-hour baseline (median and MAD per hex and hour), clusters flagged hex-hours in
   space and time into incidents, and writes each one up in a sentence: what happened, where,
   how big, the most likely cause, and what to check. A detector that can't say *why* gets
   ignored, so every alert carries its reasoning.
3. **Station siting: "what if a station opens here?"** Drop a pin and choose metro, BRT or
   feeder. MetroPulse draws the walk and feeder catchments and reports residents and jobs
   reached, estimated daily boardings, how much of that is *new* coverage versus cannibalised
   from existing hubs, the peak hour, and a 0–100 score with its formula shown. "Suggest sites"
   runs a greedy search over every hexagon and proposes the three best locations, each one
   accounting for the coverage of the ones before it.
4. **City briefings.** One click produces an editorial, print-ready briefing for the city:
   headline numbers, the busiest demand cores, walk-band coverage today and with the
   recommended sites, the week's incidents and the recommended sites, with methodology and data provenance at the end. Browsers save it as
   a PDF, so it can go straight into a WhatsApp group or a board pack.

### Why these four

They are one loop: **see** (Pulse), **notice** (Alerts), **decide** (Siting), **persuade**
(Briefing). That is the loop a planning team runs every week. Features outside it, such as
generic chat or vanity KPIs, were left out on purpose. The existing LLM agent (`/ws/agent`)
stays as a power-user tool for policy questions. The core loop does not need an LLM, so it
works offline, deterministically and for free.

## Differentiators

- **Opinionated city model out of the box.** It opens on a working model of 30 Indian cities,
  not a blank canvas. Swap in real data (AFC taps, GTFS, telecom OD matrices) as you get it.
- **Explanations, not just anomalies.** Every alert says what happened, where, how big and why.
  The reasoning is a deterministic rule trace, so it can be audited.
- **Transparent scoring.** Every siting score shows its formula and inputs. Planners can defend
  it in an appraisal meeting.
- **Built for Indian planning artefacts.** DPR alternatives analysis, CMP catchments, the
  NTOD 500–800 m walk band, and briefings sized for how decisions are actually circulated.
- **Runs in the browser.** The core loop (model, detector, siting, briefing) is plain TypeScript
  that runs client-side in under a second per city. No GPU, no LLM, no server, no map-tile
  subscription.

## Honesty about data (today)

The Pulse, Alerts, Siting and Briefing features currently run on the **MetroPulse sample city
model**: a deterministic, seeded, synthetic demand field built from each city's real-world
anchor points (CBDs, job hubs, transport hubs and residential centres from
`data/cities/*.yaml`), its published population and a sample city outline drawn around those anchors (cut at the
coast for coastal cities; not the administrative boundary). The sample week
contains scripted incidents so the detector has something to find. Every screen and every
briefing labels this. **The algorithms are real. The numbers are illustrative until a city's
own data is connected.**

## Pricing sketch (INR, annual, per city)

| Plan | Price | For | Includes |
|---|---|---|---|
| **Explorer** | Free | Students, journalists, evaluation | All 30 sample cities, Pulse, Siting, Briefings with a watermark |
| **Desk** | ₹3.5 lakh / city / year | Consultancies on a CMP or DPR engagement | Your data loaded (GTFS, survey zones, AFC extracts), unlimited scenarios, unbranded briefings, CSV/GeoJSON export, 3 seats |
| **Authority** | ₹20–40 lakh / city / year | Metro corporations, UMTAs, smart-city SPVs | Live feed connectors (AFC, GTFS-RT, ICCC), alert routing to email or WhatsApp, calibration against counts, SSO, on-prem or state data centre deployment, 25 seats |
| **API** | Usage-based | Mobility operators, proptech | Siting and catchment endpoints, embeddable map |

The first deals will be Desk licences bundled into a consultancy's tender bid, with a
price-per-study variant (₹1.5 lakh per study) for one-off DPRs.

## Roadmap

| Horizon | What | Why |
|---|---|---|
| **Now (shipped)** | Pulse playback, explained alerts, station siting with area-weighted catchments and greedy suggestions, print-ready briefings, shareable deep links to any desk view, sample model for 30 cities, India Twin (Census and VIIRS receipts), policy agent | The core loop, demonstrable offline |
| **Next (0–3 months)** | Data connectors: GTFS static (stations and routes replace the config hubs), survey traffic-analysis zones, AFC CSV import. Ward boundaries. Multi-station network scenarios ("a line, not a stop"). Saved scenarios | Turn illustrative numbers into a city's own numbers |
| **Later (3–9 months)** | Calibration against observed counts with error bars on ridership. GTFS-RT and ICCC live feeds. Alert routing (email, WhatsApp Business). Per-user auth and org workspaces. Offline "ask the city" answers grounded in the model | Move from planning tool to weekly operating tool |
| **Vision** | A city's mobility system of record: every proposal, every alert and every briefing versioned and comparable over years | The DPR becomes a living document |

## What we will not build

- A general GIS editor. QGIS exists, and we export to it.
- Real-time vehicle tracking. Operators already have AVL vendors.
- LLM-written numbers. Numbers come from the model; language models may only phrase them.

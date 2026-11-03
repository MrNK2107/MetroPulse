# MetroPulse demo script (5 minutes)

For a live demo to a metro corporation, a mobility consultancy or a judging panel. Everything runs
in the browser from `npm run dev`; there is no backend, network call or API key to fail on stage.

> 2.0 adds three beats after Siting: **Line mode** (build a corridor, see the cost sketch), **Your
> data** (load a stations CSV and watch coverage change), and **Compare** (two lines, one table).
> They are scripted at the end of this file.

## Before you start

```bash
cd frontend
npm install
npm run dev        # http://localhost:3000
```

Open these tabs in this order, and check each one has loaded:

1. `http://localhost:3000/`
2. `http://localhost:3000/desk?city=chennai`
3. `http://localhost:3000/brief?city=chennai`

Use a window at least 1280 px wide. The first load of each route compiles in dev mode (a few
seconds); after that everything is instant.

## The story in one line

"A metro station costs hundreds of crores and is decided from a five-year-old survey. MetroPulse
lets a planning team see the city move, notice what changed, test a station and brief the
commissioner, in one sitting."

## 0:00 - Landing (30 s)

- Read the headline: **Test the station before you pour the concrete.**
- Point at the map on the right: it is not a picture. It is Chennai's demand at Tuesday 19:00,
  computed in the page.
- Scroll once to the four-step loop: **see, notice, decide, persuade**. "That is the loop a planning
  team runs every week. The demo follows it."
- Click **Open the desk**.

## 0:30 - See: Pulse (60 s)

- Chennai opens at **Tue 09:00**. Name what is on screen: about 0.74 km² hexagons, trip ends this
  hour, the change against the four-week baseline, the five busiest hexagons.
- Point at the strip under the map: "Every hexagon has a weekday and a weekend profile."
- Press **play**. Narrate as it runs: the morning wave into Ambattur and the IT corridor, the evening
  release, then the flatter weekend. Pause on a weekend hour.
- Point at the coloured diamonds on the timeline: "These are this week's incidents."
- Say the honesty line now, before anyone asks: "This is our sample city model, built from
  Chennai's real anchors and population with scripted incidents. The algorithms are real; the
  numbers become real when we connect the city's own data." The banner under the header says the
  same.

## 1:30 - Notice: Alerts (75 s)

- Click **Alerts**. Three incidents, sorted by size.
- Open **Surge near T Nagar, Fri 18:00-23:00**. The timeline jumps to Friday 20:00 and the hexagons
  are outlined on the map.
- Read the explanation: "2.1x the four-week same-hour median at the peak, about N extra trips over
  five hours." Then the **likely cause** (a crowd release after a large event) and **what to check**
  (event permits and police bandobast, extra trains).
- Expand **Rule trace**: "A detector that cannot say why gets ignored. This one shows every step:
  median and MAD baseline, robust z at least 4 and a 30% change, joined in space and time, nearest
  anchor, and the rule that fired. An engineer can audit it."
- Click the **Drop near Velachery** card: a Tuesday-morning drop inside the commute peak, read as a
  supply disruption (waterlogging, closure). "Same detector, opposite direction, different rule."

## 2:45 - Decide: Siting (75 s)

- Click **Siting**. Keep **Metro** selected.
- Click on the map somewhere busy but away from Chennai Central, for example south-west of T Nagar.
  The walk band (800 m) and feeder band (2.5 km) appear.
- Read the panel: score out of 100, estimated daily boardings, **new coverage** (the share not
  already served by an existing hub), residents and jobs in the walk band, the weekday boardings
  curve, and the formula. "No black box. The score is 60 for volume plus 40 for new coverage, and
  the inputs are on screen."
- Now click next to **Chennai Central**: new coverage falls because that demand is already served.
  "It knows about cannibalisation."
- Click **Suggest 3 sites**. Three numbered rings appear. "Greedy search over every hexagon. Each
  pick only counts demand the existing hub and the earlier picks don't serve, so they spread into a
  network." Click suggestion **2** in the list to pin and score it.
- Switch the mode to **BRT** or **Feeder** and show the bands shrink.

## 4:00 - Persuade: Briefing (45 s)

- Click **Briefing** (top right).
- The headline is written from the numbers: incidents this week and where the next station belongs.
- Point at **walk-band coverage today → with the 3 sites**, the demand map with the recommended
  sites, the incident write-ups, the site table and the methodology box with the data caveat.
- Click **Print or save as PDF** to show the clean print layout. "This goes straight into the board
  pack or a WhatsApp group."

## 4:45 - Close (15 s)

- Back on the desk, change the city to **Mumbai**: the whole loop recomputes for a new city in about
  a second. "Thirty Indian cities, out of the box."
- Copy the address bar: "Every view is a link. Send the exact incident or the exact site to a
  colleague."
- Close: "Next step: we load your GTFS stations, survey zones and AFC extracts, and these become
  your numbers."

## Questions you will get

| Question | Answer |
|---|---|
| Is this real data? | Not yet. Every screen says it is a sample model. The detector, siting and scoring are the production algorithms; the demand field is synthetic until a city's data is connected. |
| How accurate are the boardings? | Uncalibrated. They come from fixed capture rates per mode. Calibration against observed counts, with error bars, is on the roadmap. |
| Why not use an LLM to explain alerts? | Explanations come from deterministic rules so they are auditable and reproducible. Language models may phrase numbers, never produce them. |
| Where does it run? | In the browser. No GPU, no server for the core loop, no map-tile subscription. A state data centre deployment is possible for the Authority plan. |
| What does it cost? | See the pricing section on the landing page and in [`PRODUCT.md`](PRODUCT.md). |

## If something goes wrong

- **Blank page or slow first load:** dev mode compiles each route on first visit. Load all three
  tabs before you start.
- **A shared link opens the wrong view:** check the query string; valid tabs are `pulse`, `alerts`
  and `siting`, and `incident` is 1-based.
- **Chennai opens instead of the city you linked:** the city id is unknown and the desk fell back
  to Chennai. Use an id from the city picker (lowercase, `delhi_ncr` for Delhi).

## 4:00 - Line mode, Your data, Compare (90 s, the 2.0 beats)

- On **Siting**, click **Line**. Click three points along a corridor (or press **Suggest a line**).
  Read the network figures: boardings net of the line's own cannibalisation, new share, length,
  the spacing warning if two stops are too close, the cost sketch and **cost per daily boarding**.
  "Every figure shows its formula, and the cost table is editable, so a DPR team can put their own
  rates in."
- Press **Save line**, then **Copy link**. "The link carries the line itself; nothing is stored on a
  server."
- Click **Your data** in the header. Drop a stations CSV (five rows is enough). The banner changes
  to *Your data · Stations: 5 from stations.csv* and the map now shows your stations as the
  existing hubs. "Coverage and cannibalisation are now measured against this network. With a
  counts CSV, the boardings scale to the observed numbers and the formula says so."
- Press **Compare**. Two lines side by side, a delta column, and **Download CSV** gives the
  alternatives table a DPR annex needs.
- Close on `/city/chennai`: "Every city has a public page, and the same numbers are an API call
  away."

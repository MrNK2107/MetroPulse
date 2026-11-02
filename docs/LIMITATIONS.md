# MetroPulse limitations

What MetroPulse can and cannot tell you today, part by part. The README's "Known gaps" lists the
engineering gaps; this page is about the numbers.

## The desk (Pulse, Alerts, Siting, Briefing)

### 1. The demand field is a sample model, not observed travel

Every number on the desk comes from the **MetroPulse sample city model**
(`frontend/src/lib/pulse/model.ts`): a seeded, synthetic demand field. Residents and jobs are
spread around each city's configured anchor points (CBDs, job hubs, transport hubs, residential
centres in `data/cities/*.yaml`) and scaled to its published population. Hourly demand comes from
fixed weekday and weekend profiles for residents, jobs, leisure and hubs.

**Impact:** the map shows a plausible shape of a city's movement, not its measured movement. A
dark hexagon means "the model puts demand here", not "people were counted here". Every screen and
every briefing says so.

### 2. The incidents are scripted

Each sample week carries the same three kinds of scripted incident (an evening event surge, a
waterlogging drop in a residential area, a mid-shift surge at an employer) on top of ordinary
noise. The detector is real and is not told where they are, but finding them proves the detector
works, not that those events happened.

### 3. Siting numbers rest on assumed capture rates

Boardings are the residents and jobs inside the walk and feeder bands times a fixed capture rate
per mode (metro 4% walk / 1% feeder, BRT 3% / 0.8%, feeder bus 1.5% / 0.4%). These rates are
assumptions, not calibrated against counts. The 0-100 score is scaled against a reference daily
boardings figure per mode (metro 50,000, BRT 15,000, feeder bus 3,000), so a score of 100 means
"at or above the reference", not "the best possible site".

### 4. Existing coverage is a lower bound

"Existing hubs" are the city's configured transport anchors, each given a metro walk band. Most
cities have only one or two such anchors, so real existing coverage is higher and the "new
coverage" share of a proposal is overstated.

### 5. Sample outlines are not administrative boundaries

Each city's outline is drawn around its anchors and population and cut at the coast for coastal
cities. It is not the municipal or metropolitan boundary.

### 6. No calibration, no error bars

Nothing on the desk has been validated against ridership, AFC taps or survey counts yet. That is
the next step on the roadmap (`docs/PRODUCT.md`): connect a city's own data, then calibrate.

## The India Twin

### 7. Few indicators

Only Census 2011 (five population indicators) and VIIRS night lights have adapters. The other
sources in the registry are metadata only.

### 8. Census 2011 mapped onto today's districts

Districts created after 2011 get values apportioned by area from their 2011 parent district. These
carry the `Pattern` trust label, not `Fact`, and are estimates. Area apportionment assumes people
are spread evenly within the parent district, which they are not.

### 9. No real-data build published yet

The real build needs seven source files, some behind a login or captcha
(`data/twin/manual/README.md`). Until someone runs it, the twin shows a "not built" panel or the
synthetic test fixtures.

## The planning agent

### 10. Estimates, not forecasts

The agent has no simulation tool. `compare_sectors` multiplies each requested sector change by that
sector's weight in the city config and ranks the results: a static, directional estimate. City
baselines in the YAML configs (GDP, employment, sector weights) are estimates, because India does
not publish city-level GDP or unemployment.

### 11. Case studies are summaries

The 20 case studies describe real Indian urban events with generalised outcomes. They are not
quantitative evidence.

### 12. "Realtime" signals are news proxies

The mobility, jobs and land-value signals are keyword sentiment over news articles. A negative
score means more negative coverage, not a measured decline. No current screen shows them.

## In short

- **The algorithms are real; the desk numbers are illustrative** until a city's own data is
  connected.
- **Twin values carry receipts.** Check the source, period and trust label before you quote one.
- **Use it to explore and to frame a study,** not as the study's final numbers.

# 0002. A user's own city data is imported client-side and never uploaded

**Status:** Accepted (2026-11-03)

## Context

Until 2.0 the desk ran only on a synthetic city model, and every screen said the numbers were
illustrative until a city's own data was connected. Consultancies and metro corporations hold that data
(a boundary, a GTFS feed or station list, observed boardings), but it is often under contract or a
non-disclosure agreement, and sending it to a third-party server is a reason to say no. A server-side
import would also need accounts, storage, retention rules and a security review before its first use.

## Decision

Imports happen in the browser. Parsers in `frontend/src/lib/pulse/import/` read GeoJSON boundaries, GTFS
static zips, stations CSVs and counts CSVs locally. There is no upload endpoint. The result is reduced to
derived data only (the boundary ring, a station list, per-station daily boardings) and stored in
`localStorage` under `metropulse.citydata.<cityId>.v1`; a GTFS zip of tens of megabytes becomes a few
kilobytes. Storage access is wrapped in try/catch, and a blocked store falls back to memory for the
session. Every screen says what was loaded.

## Consequences

- A user can try MetroPulse on confidential data without a procurement conversation, and the privacy page
  can say plainly that nothing leaves the browser.
- Data does not follow the user across devices, and clearing the browser clears it. Cloud workspaces are
  the first paid feature and will need their own record.
- Raw files are not kept, so re-deriving after a parser change means loading the file again.
- Parsers must be pure and unit-tested on fixtures, since there is no server log to debug a bad import.

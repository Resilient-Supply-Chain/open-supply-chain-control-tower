# SR-99 Corridor, January 2023 Atmospheric River — Transportation Data Extracts

Source datasets for the OACT × PATH SR-99 freight-continuity pilot. These are
small, corridor-filtered extracts of public Caltrans PeMS downloads, used to
check whether the January 2023 storm can be reconstructed end to end from
public data: weather trigger → road closure → traffic impact → freight exposure.

Nothing in the dashboard or agent reads these files at runtime (see
*Repository conventions* in [`MAINTAINERS.md`](../../../MAINTAINERS.md)).

- **Corridor:** California State Route 99 (PeMS freeway number `99`)
- **Districts:** Caltrans Districts 3, 6 and 10 (Central Valley)
- **Event window:** 2023-01-09 to 2023-01-16
- **Anchor event:** SR-99 flood closure near Woodbridge Rd, Lodi–Acampo
  (San Joaquin County, absolute postmile ~267–270), 2023-01-16

## Files

| File | Rows | Grain | What it is |
|------|-----:|-------|------------|
| `station_metadata_sr99.csv` | 1,201 | 1 row per detector station | Every SR-99 PeMS station in D3/D6/D10: ID, direction, county, state and absolute postmile, lat/lon, lane type, lanes |
| `station_hour_sr99_lodi_acampo_2023-01-15_16.csv` | 288 | 1 row per station per hour | Hourly flow, occupancy, speed and % observed for the 6 mainline stations in the closure zone, Jan 15–16 |
| `station_hour_sr99_daily_2023-01-09_16.csv` | 24 | 1 row per district per day | Corridor daily summary over the storm window: stations, median % observed, average and minimum speed |
| `chp_incidents_sr99_2023-01-09_16.csv` | 464 | 1 row per incident | All CHP incidents on SR-99 in the storm window, with incident type, location, lat/lon and postmiles |
| `chp_incident_detail_sr99_flood_closure_2023-01-09_16.csv` | 327 | 1 row per dispatcher log entry | Free-text log for the 22 flood/closure incidents only (phone numbers and plates redacted) |
| `tmg_trucks_sr99_2021-06.csv` | 2,700 | 1 row per station per day per vehicle class | Truck classification counts on SR-99, June 2021 |
| `build_extracts.py` | — | — | Rebuilds every file above from the raw PeMS downloads |

## Key fields

**Join keys.** Traffic, closure and truck layers join on **freeway + absolute
postmile** (spatial) and **timestamp** (temporal). The weather layer
(`Asset_Data_Team/.../california_risk_model_data_dec2022_mar2023.csv`) joins on
**county + date**.

- `Abs_PM` / `abs_postmile` — continuous statewide postmile along the route.
  Use this for joins.
- `State_PM` / `state_postmile` — Caltrans' official postmile. It resets at each
  county line and can carry letter prefixes (e.g. `R21.407`), so it is not a
  reliable join key on its own.
- `pct_observed` — share of the hour backed by working detectors rather than
  PeMS imputation. A station with `0` was offline.
- `lane_type` — `ML` is mainline; other values are ramps, HOV and collector lanes.
- CHP `description` — incident type. Weather-related closures appear as
  `FLOOD-Roadway Flooding`, `CLOSURE-Closure of a Road` and `CLOSURE of a Road`
  (two spellings exist), plus `SLIDE-Mud/Dirt/Rock`.
- TMG `vehicle_class` — `0` is the total truck count for the station-day;
  classes `2..N` are axle classes that sum to the total.

## What the extracts show

- **Coverage.** SR-99 has 740 mainline stations across D3/D6/D10; 73% reported
  data during the storm window (I-5: 312 stations, 59%).
- **Closure capture.** CHP logged roadway flooding at Woodbridge Rd (abs PM
  268.4) on Jan 15 and Acampo Rd (269.6) on Jan 16, then `CLOSURE-Closure of a
  Road` at abs PM 267.6 at 12:20 on Jan 16. The Woodbridge Rd PeMS stations
  dropped from about 65 mph to a minimum of 4.3 mph that midday.
- **Freight exposure.** SR-99 truck-census stations average about 3,090 trucks
  per day (I-5: about 2,913).

## Reproducing

PeMS does not allow programmatic downloads. Fetch the raw files by hand from the
[PeMS Data Clearinghouse](https://pems.dot.ca.gov/) (free account; text format):

| Clearinghouse type | District | Period |
|--------------------|----------|--------|
| Station Metadata | 3, 6, 10 | file in effect for Jan 2023 |
| Station Hour | 3, 6, 10 | January 2023 |
| CHP Incidents Month | statewide | January 2023 |
| Census Trucks Day | statewide | June 2021 |

Then run:

```bash
python data/raw/sr99_jan2023/build_extracts.py --raw-dir /path/to/downloads
```

## Known limitations

- **Detector gaps.** Roughly a third of rural mainline stations were offline
  during the storm, so traffic coverage has spatial gaps.
- **Metadata dates.** The station metadata files are dated 2022-05-05 (D6),
  2022-10-07 (D10) and 2023-01-05 (D3). They stand in for the January 2023
  layout but are not exact-day snapshots.
- **CHP is not the official closure record.** CHP incident logs are a
  disruption proxy. The authoritative Caltrans Lane Closure System archive has
  not been obtained.
- **CHP detail is free text.** Entries use dispatch codes (e.g. `1039`) and
  abbreviations. Only flood/closure incidents are included, with phone numbers
  and licence plates redacted; the full log contains more personal detail and
  is deliberately not published here.
- **Truck data is 2021.** PeMS truck census data ends in 2021 and is used as a
  stable proxy. Census stations are sparse (2–4 per corridor), enough to rank
  corridors but not individual segments.
- **One event.** These extracts cover a single storm. Stage 2 out-of-time
  validation needs additional events.

## Provenance

Source: California Department of Transportation, Performance Measurement System
(PeMS), https://pems.dot.ca.gov/. CHP incident records are distributed through
PeMS. Downloaded September 2026 by Hao He for the OACT feasibility study.

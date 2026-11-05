#!/usr/bin/env python3
"""
Build the SR-99 / January 2023 extracts in this folder from raw Caltrans PeMS
Data Clearinghouse downloads.

PeMS does not allow programmatic downloads, so the raw files must be fetched by
hand from https://pems.dot.ca.gov/ (Tools -> Data Clearinghouse, text format):

  Station Metadata    : D3, D6, D10   -> d03_text_meta_*.txt, ...
  Station Hour        : D3, D6, D10, Jan 2023 -> d03_text_station_hour_2023_01.txt.gz, ...
  CHP Incidents Month : statewide, Jan 2023 -> all_text_chp_incidents_month_2023_01.txt.gz
                        (the zip also contains all_text_chp_incident_det_month_2023_01.txt.gz)
  Census Trucks Day   : statewide, Jun 2021 -> all_text_tmg_trucks_day_2021_06.txt.gz

Usage:
  python build_extracts.py --raw-dir /path/to/downloaded/files

Outputs (written next to this script):
  station_metadata_sr99.csv
  station_hour_sr99_lodi_acampo_2023-01-15_16.csv
  station_hour_sr99_daily_2023-01-09_16.csv
  chp_incidents_sr99_2023-01-09_16.csv
  chp_incident_detail_sr99_flood_closure_2023-01-09_16.csv
  tmg_trucks_sr99_2021-06.csv
"""
import argparse
import glob
import os

import pandas as pd

OUT = os.path.dirname(os.path.abspath(__file__))
FWY = 99
WIN_START, WIN_END = "2023-01-09", "2023-01-16 23:59:59"
# SR-99 Lodi-Acampo / Woodbridge Rd closure zone (absolute postmile)
ZONE_PM = (266.0, 271.0)

# Raw PeMS station_hour, CHP incident and TMG files have no header row.
STATION_HOUR_COLS = {0: "timestamp", 1: "station", 2: "district", 3: "freeway", 4: "direction",
                     5: "lane_type", 6: "station_length", 7: "samples", 8: "pct_observed",
                     9: "total_flow", 10: "avg_occupancy", 11: "avg_speed"}
CHP_COLS = ["incident_id", "cc_code", "incident_number", "timestamp", "description", "location",
            "area", "zoom_map", "tb_xy", "latitude", "longitude", "district", "county_fips",
            "city_fips", "freeway", "direction", "state_postmile", "abs_postmile",
            "severity", "duration_min"]
CHP_DET_COLS = ["incident_id", "detail_id", "timestamp", "entry"]
TMG_COLS = {0: "timestamp", 1: "station", 3: "freeway", 4: "direction", 8: "abs_postmile",
            9: "lane_type", 12: "vehicle_class", 13: "truck_volume"}


def find(raw_dir, pattern):
    files = sorted(glob.glob(os.path.join(raw_dir, "**", pattern), recursive=True))
    if not files:
        raise SystemExit(f"No files matching {pattern} under {raw_dir}")
    return files


def read_chp_detail(path):
    """The detail log's free-text entry can contain commas and line breaks, so it is
    not valid CSV. Split each record on the first three commas and fold continuation
    lines (lines that do not start with a numeric incident id) into the previous entry."""
    import gzip
    rows = []
    with gzip.open(path, "rt", encoding="latin-1") as fh:
        for line in fh:
            line = line.rstrip("\n")
            parts = line.split(",", 3)
            if len(parts) == 4 and parts[0].isdigit() and parts[1].isdigit():
                rows.append(parts)
            elif rows:
                rows[-1][3] += " " + line.strip()
    det = pd.DataFrame(rows, columns=CHP_DET_COLS)
    det["incident_id"] = det["incident_id"].astype("int64")
    det["entry"] = det["entry"].str.strip()
    return det


def main(raw_dir):
    # 1. Station metadata (tab-delimited, has header)
    meta = pd.concat([pd.read_csv(f, sep="\t") for f in find(raw_dir, "d*_text_meta_*.txt")],
                     ignore_index=True)
    meta99 = meta[meta["Fwy"] == FWY].sort_values(["District", "Abs_PM"])
    meta99.to_csv(os.path.join(OUT, "station_metadata_sr99.csv"), index=False)
    zone_ids = set(meta99[(meta99["Type"] == "ML") & meta99["Abs_PM"].between(*ZONE_PM)]["ID"])

    # 2. Station hour: closure-zone hourly rows + corridor daily summary
    sh = pd.concat([pd.read_csv(f, header=None, usecols=list(STATION_HOUR_COLS), compression="gzip")
                    .rename(columns=STATION_HOUR_COLS)
                    for f in find(raw_dir, "d*_text_station_hour_2023_01.txt.gz")], ignore_index=True)
    sh["timestamp"] = pd.to_datetime(sh["timestamp"], format="%m/%d/%Y %H:%M:%S")
    sh99 = sh[(sh["freeway"] == FWY) & (sh["lane_type"] == "ML") &
              (sh["timestamp"] >= WIN_START) & (sh["timestamp"] <= WIN_END)]
    zone = sh99[sh99["station"].isin(zone_ids) & (sh99["timestamp"] >= "2023-01-15")]
    zone.sort_values(["station", "timestamp"]).to_csv(
        os.path.join(OUT, "station_hour_sr99_lodi_acampo_2023-01-15_16.csv"), index=False)
    daily = (sh99.assign(date=sh99["timestamp"].dt.date)
             .groupby(["date", "district"])
             .agg(stations=("station", "nunique"),
                  stations_reporting=("pct_observed", lambda s: int((s > 0).sum() > 0)),
                  median_pct_observed=("pct_observed", "median"),
                  avg_speed=("avg_speed", "mean"),
                  min_speed=("avg_speed", "min"))
             .reset_index())
    daily = daily.drop(columns="stations_reporting").round(2)
    daily.to_csv(os.path.join(OUT, "station_hour_sr99_daily_2023-01-09_16.csv"), index=False)

    # 3. CHP incidents on SR-99 in the storm window, plus their detail log entries
    chp = pd.read_csv(find(raw_dir, "all_text_chp_incidents_month_2023_01.txt.gz")[0],
                      header=None, names=CHP_COLS, compression="gzip")
    chp["timestamp"] = pd.to_datetime(chp["timestamp"], format="%m/%d/%Y %H:%M:%S")
    chp99 = chp[(chp["freeway"].astype(str) == str(FWY)) &
                (chp["timestamp"] >= WIN_START) & (chp["timestamp"] <= WIN_END)]
    chp99.sort_values("timestamp").to_csv(
        os.path.join(OUT, "chp_incidents_sr99_2023-01-09_16.csv"), index=False)
    # Detail entries are dispatcher free text. The full log contains tow-company phone
    # numbers, licence plates and occasional caller names, so only entries for the
    # flood/closure incidents are published, with phone and plate patterns redacted.
    det = read_chp_detail(find(raw_dir, "all_text_chp_incident_det_month_2023_01.txt.gz")[0])
    flood_ids = set(chp99.loc[chp99["description"].str.contains("FLOOD|CLOSURE", na=False),
                              "incident_id"])
    det = det[det["incident_id"].isin(flood_ids)].copy()
    det["entry"] = (det["entry"]
                    .str.replace(r"\(?\b\d{3}\)?[-\s.]?\d{3}[-\s.]?\d{4}\b", "[PHONE]", regex=True)
                    .str.replace(r"\b\d[A-Z]{3}\d{3}\b", "[PLATE]", regex=True))
    det.sort_values(["incident_id", "timestamp"]).to_csv(
        os.path.join(OUT, "chp_incident_detail_sr99_flood_closure_2023-01-09_16.csv"), index=False)

    # 4. TMG truck census on SR-99 (class 0 = total trucks; classes 2..N = axle classes)
    tmg = pd.read_csv(find(raw_dir, "all_text_tmg_trucks_day_2021_06.txt.gz")[0],
                      header=None, usecols=list(TMG_COLS), compression="gzip").rename(columns=TMG_COLS)
    tmg[tmg["freeway"] == FWY].to_csv(os.path.join(OUT, "tmg_trucks_sr99_2021-06.csv"), index=False)

    for f in sorted(glob.glob(os.path.join(OUT, "*.csv"))):
        print(f"{os.path.basename(f):55s} {sum(1 for _ in open(f)) - 1:>7,} rows")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw-dir", required=True, help="Folder containing the raw PeMS downloads")
    main(ap.parse_args().raw_dir)

#!/usr/bin/env python3
"""
Build truck_aadt_sr99_2021-2024.csv: Caltrans Truck AADT for SR-99, 2021-2024,
with an estimated absolute postmile so it joins to the PeMS and CHP extracts.

Source: Caltrans Traffic Census Program, one Excel workbook per year
(https://dot.ca.gov/programs/traffic-operations/census). The workbooks are
downloaded directly; pass --raw-dir to use local copies instead.

Join method: Truck AADT postmiles are county-relative. PeMS station metadata
(station_metadata_sr99.csv in this folder) carries both the county-relative
State_PM and the continuous Abs_PM for each station, so absolute postmile is
interpolated within each county from those station pairs. Rows outside the
range of PeMS stations in their county are left blank (abs_pm_est = NaN).

Usage:
  python build_truck_aadt.py                 # download from Caltrans
  python build_truck_aadt.py --raw-dir DIR   # use local workbooks
"""
import argparse
import io
import os
import urllib.request

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "https://dot.ca.gov/-/media/dot-media/programs/traffic-operations/documents/census"
FILES = {
    2021: "2021/2021-truck-aadtt-ca.xlsx",
    2022: "2022/2022-truck-aadt.xlsx",
    2023: "2023/2023-truck-aadt-a11y.xlsx",
    2024: "2024/2024-truck-aadt-a11y.xlsx",
}
# Caltrans county abbreviation -> county FIPS code used in PeMS metadata
CNTY_FIPS = {"TEH": 103, "BUT": 7, "SUT": 101, "SAC": 67, "SJ": 77, "STA": 99,
             "MER": 47, "MAD": 39, "FRE": 19, "TUL": 107, "KER": 29}


def load_year(year, raw_dir):
    path = FILES[year]
    if raw_dir:
        src = os.path.join(raw_dir, os.path.basename(path))
    else:
        req = urllib.request.Request(f"{BASE}/{path}", headers={"User-Agent": "Mozilla/5.0"})
        src = io.BytesIO(urllib.request.urlopen(req, timeout=60).read())
    df = pd.read_excel(src, sheet_name=1, dtype=str)  # sheet 0 is a blank preface
    df.columns = [c.replace("EST/VER_", "EST_") for c in df.columns]  # 2022 naming
    df = df[df["RTE"].str.lstrip("0") == "99"].copy()
    df.insert(0, "YEAR", year)
    return df


def abs_pm_lookup():
    meta = pd.read_csv(os.path.join(HERE, "station_metadata_sr99.csv"))
    meta["spm"] = meta["State_PM"].astype(str).str.replace(r"[A-Za-z]", "", regex=True).astype(float)
    return {c: g.groupby("spm")["Abs_PM"].median().sort_index() for c, g in meta.groupby("County")}


def main(raw_dir):
    df = pd.concat([load_year(y, raw_dir) for y in FILES], ignore_index=True)
    for c in ["POSTMILE", "VEHICLE_AADT_TOTAL", "TOT_TRK_AADT", "TRK_PERCENT_TOT"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    lookup = abs_pm_lookup()

    def to_abs(cnty, pm):
        s = lookup.get(CNTY_FIPS.get(cnty))
        if s is None or len(s) < 2 or pm < s.index.min() - 1 or pm > s.index.max() + 1:
            return np.nan
        return round(float(np.interp(pm, s.index.values, s.values)), 3)

    df["abs_pm_est"] = [to_abs(c, p) for c, p in zip(df["CNTY"], df["POSTMILE"])]
    out = os.path.join(HERE, "truck_aadt_sr99_2021-2024.csv")
    df.to_csv(out, index=False)
    print(f"{os.path.basename(out)}: {len(df)} rows; "
          f"{df['abs_pm_est'].notna().sum()} with abs_pm_est")
    print(df.groupby("YEAR").size().to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw-dir", help="Folder with the Caltrans Truck AADT workbooks (optional)")
    main(ap.parse_args().raw_dir)

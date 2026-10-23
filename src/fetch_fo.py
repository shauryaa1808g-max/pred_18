"""Fetch NSE F&O UDiFF bhavcopy, keep only rows with TckrSymb == 'BSE' (stock futures/options), cache compactly.

Source: nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_YYYYMMDD_F_0000.csv.zip  (exchange end-of-day, public)
"""
from __future__ import annotations

import io
import json
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests

from fetch_nse import CA, UA

OUT = Path("data/raw/fo_bse")


def url(d: str) -> str:
    return f"https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{d}_F_0000.csv.zip"


def one(d: str) -> tuple[str, str]:
    p = OUT / f"{d}.csv"
    if p.exists():
        return d, "cached"
    s = requests.Session()
    s.headers["User-Agent"] = UA
    for k in range(4):
        try:
            r = s.get(url(d), timeout=60, verify=CA)
            if r.status_code == 404:
                return d, "404"
            if r.status_code == 200 and r.content[:2] == b"PK":
                z = zipfile.ZipFile(io.BytesIO(r.content))
                df = pd.read_csv(z.open(z.namelist()[0]))
                df = df[df["TckrSymb"] == "BSE"]
                df.to_csv(p, index=False)
                return d, f"rows={len(df)}"
        except Exception as e:  # noqa: BLE001
            last = str(e)
        time.sleep(2 * (k + 1))
    return d, "FAILED"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    man = json.loads(Path("data/raw/manifest.json").read_text())
    start = sys.argv[1] if len(sys.argv) > 1 else "2024-11-15"
    days = [k.replace("-", "") for k, r in man.items() if r["idx"] == 200 and k >= start]
    with ThreadPoolExecutor(max_workers=5) as ex:
        res = list(ex.map(one, days))
    bad = [r for r in res if r[1] in ("FAILED", "404")]
    print(f"days={len(days)} ok={sum(r[1] not in ('FAILED','404') for r in res)} bad={len(bad)}", bad[:20])


if __name__ == "__main__":
    main()

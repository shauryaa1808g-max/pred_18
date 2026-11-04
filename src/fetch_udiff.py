"""Fetch NSE CM UDiFF bhavcopy (published ~16:34 IST, earlier than sec_bhavdata_full which carries delivery data) for given dates -> data/raw/udiff/YYYYMMDD.zip
Usage: python3 src/fetch_udiff.py 2026-10-13 [more dates]"""
import sys, requests
from pathlib import Path
from fetch_nse import CA, UA
out = Path("data/raw/udiff"); out.mkdir(parents=True, exist_ok=True)
for ds in sys.argv[1:]:
    k = ds.replace("-", "")
    r = requests.get(f"https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{k}_F_0000.csv.zip", headers={"User-Agent": UA}, timeout=60, verify=CA)
    print(ds, r.status_code, len(r.content))
    if r.status_code == 200 and r.content[:2] == b"PK":
        (out / f"{k}.zip").write_bytes(r.content)

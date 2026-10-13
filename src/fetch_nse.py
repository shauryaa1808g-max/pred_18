"""Download raw NSE end-of-day archives (cash bhavcopy + index closes) into a local cache.

Sources (all public exchange archives, no login):
  * Index closes : nsearchives.nseindia.com/content/indices/ind_close_all_DDMMYYYY.csv
  * Cash bhavcopy: nsearchives.nseindia.com/products/content/sec_bhavdata_full_DDMMYYYY.csv  (has delivery data)
                   nsearchives.nseindia.com/content/historical/EQUITIES/YYYY/MON/cmDDMONYYYYbhav.csv.zip (legacy, no delivery)
A weekday on which the index file returns HTTP 404 is treated as an exchange holiday.
Everything is cached verbatim; a manifest records what happened for every weekday so gaps are auditable.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

BASE = "https://nsearchives.nseindia.com"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
CA = os.environ.get("REQUESTS_CA_BUNDLE") or "/root/.ccr/ca-bundle.crt"
SEC_BHAV_FIRST = dt.date(2019, 10, 1)  # earliest date probed with sec_bhavdata_full available; earlier dates fall back to legacy


def urls(d: dt.date) -> dict[str, str]:
    ddmmyyyy = d.strftime("%d%m%Y")
    mon = d.strftime("%b").upper()
    return {
        "idx": f"{BASE}/content/indices/ind_close_all_{ddmmyyyy}.csv",
        "sec": f"{BASE}/products/content/sec_bhavdata_full_{ddmmyyyy}.csv",
        "legacy": f"{BASE}/content/historical/EQUITIES/{d.year}/{mon}/cm{d.day:02d}{mon}{d.year}bhav.csv.zip",
    }


def get(session: requests.Session, url: str, tries: int = 4) -> tuple[int, bytes]:
    last = (0, b"")
    for k in range(tries):
        try:
            r = session.get(url, timeout=40, verify=CA)
            if r.status_code in (200, 404):
                return r.status_code, r.content
            last = (r.status_code, r.content)
        except requests.RequestException as e:  # noqa: PERF203
            last = (-1, str(e).encode())
        time.sleep(1.5 * (k + 1))
    return last


def one_day(d: dt.date, root: Path) -> dict:
    s = requests.Session()
    s.headers["User-Agent"] = UA
    u = urls(d)
    key = d.strftime("%Y%m%d")
    rec = {"date": d.isoformat(), "idx": None, "bhav": None}
    idx_path = root / "idx" / f"{key}.csv"
    if idx_path.exists():
        rec["idx"] = 200
    else:
        code, body = get(s, u["idx"])
        rec["idx"] = code
        if code == 200 and body[:5] == b"Index":
            idx_path.write_bytes(body)
        elif code == 200:
            rec["idx"] = "bad_body"
    if rec["idx"] == 404:
        return rec  # holiday / no session
    sec_path = root / "sec" / f"{key}.csv"
    leg_path = root / "legacy" / f"{key}.zip"
    if sec_path.exists():
        rec["bhav"] = "sec"
        return rec
    if leg_path.exists():
        rec["bhav"] = "legacy"
        return rec
    order = ["sec", "legacy"] if d >= SEC_BHAV_FIRST else ["legacy", "sec"]
    for kind in order:
        code, body = get(s, u[kind])
        if code == 200 and kind == "sec" and body[:6] == b"SYMBOL":
            sec_path.write_bytes(body)
            rec["bhav"] = "sec"
            return rec
        if code == 200 and kind == "legacy" and body[:2] == b"PK":
            leg_path.write_bytes(body)
            rec["bhav"] = "legacy"
            return rec
    rec["bhav"] = "MISSING"
    return rec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2017-02-03")  # BSE Ltd listing date on NSE
    ap.add_argument("--end", required=True)
    ap.add_argument("--root", default="data/raw")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    root = Path(a.root)
    for sub in ("idx", "sec", "legacy"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    d0, d1 = dt.date.fromisoformat(a.start), dt.date.fromisoformat(a.end)
    days = [d0 + dt.timedelta(n) for n in range((d1 - d0).days + 1) if (d0 + dt.timedelta(n)).weekday() < 5]
    out = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(one_day, d, root): d for d in days}
        for i, f in enumerate(as_completed(futs), 1):
            out.append(f.result())
            if i % 100 == 0:
                print(f"{i}/{len(days)} done in {time.time()-t0:.0f}s", flush=True)
    out.sort(key=lambda r: r["date"])
    man = root / "manifest.json"
    prev = json.loads(man.read_text()) if man.exists() else {}
    for r in out:
        prev[r["date"]] = r
    man.write_text(json.dumps(dict(sorted(prev.items())), indent=0))
    bad = [r for r in out if r["idx"] not in (200, 404) or r["bhav"] == "MISSING"]
    print(f"weekdays={len(days)} sessions={sum(r['idx']==200 for r in out)} holidays={sum(r['idx']==404 for r in out)} problems={len(bad)}")
    for r in bad[:40]:
        print("PROBLEM", r)


if __name__ == "__main__":
    sys.exit(main())

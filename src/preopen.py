"""NSE pre-open call auction for BSE: the OPENING PRICE as the exchange itself computes it, readable from 09:00 and final at about 09:09 IST (trading starts 09:15).

  python3 src/preopen.py            # fetch now, print in plain words, append the snapshot to results/preopen/<date>.jsonl
  python3 src/preopen.py --symbol CDSL

The indicative equilibrium price (IEP) moves while orders are entered (09:00-09:08) and is fixed at about 09:08-09:09 (the final price appears on the endpoint stamped 09:09:00 to 09:09:34 on 15 and 16 Oct; secondary sources say NSE changed the pre-open timetable from 7 Sep 2026, unconfirmed: the tool therefore calls the price final only when NSE's finalPrice field is filled); NSE uses it as the official open, so from then on this is
the opening price to within a tick or two, not a forecast.  Source: NSE https://www.nseindia.com/api/market-data-pre-open?key=ALL (public page data, unofficial API, may change).
After the open, the snapshot stays on the endpoint until the next pre-open, so a call after 09:15 returns that morning's final pre-open.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import time
from pathlib import Path

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
JAR = "/tmp/nse_cookies.txt"
URL = "https://www.nseindia.com/api/market-data-pre-open?key=ALL"


def fetch(symbol: str = "BSE", tries: int = 3) -> dict:
    last = None
    for k in range(tries):
        subprocess.run(["curl", "-sS", "--http1.1", "-m", "25", "-A", UA, "-c", JAR, "-o", "/dev/null", "https://www.nseindia.com/"], capture_output=True)   # cookies (the page itself may answer 403)
        out = subprocess.run(["curl", "-sS", "--http1.1", "-m", "40", "-A", UA, "-b", JAR, "-H", "Accept: application/json", "-H", "Referer: https://www.nseindia.com/market-data/pre-open-market-cm-and-emerge-market", URL], capture_output=True, text=True)
        try:
            j = json.loads(out.stdout)
            for r in j["data"]:
                if r["metadata"]["symbol"] == symbol:
                    return {"snapshot_timestamp": j.get("timestamp"), "meta": r["metadata"], "pre": r["detail"]["preOpenMarket"]}
            raise KeyError(f"{symbol} not in pre-open list")
        except Exception as e:                                             # noqa: BLE001
            last = e; time.sleep(2 + 2 * k)
    raise SystemExit(f"could not read NSE pre-open data: {last}")


def words(s: dict, symbol: str = "BSE") -> str:
    m, p = s["meta"], s["pre"]; iep = float(p["IEP"]); prev = float(p["prevClose"])
    t = p["lastUpdateTime"]; hhmmss = t[-8:]
    fin = float(p.get("finalPrice") or 0)
    final = fin > 0                       # NSE fills finalPrice only once the auction has matched (16 Oct: IEP 3,450 at 09:08:34 with finalPrice 0; finalPrice 3,450 stamped 09:09:00); a clock rule would call an indicative price final
    if final: iep = fin
    book = sorted(p["preopen"], key=lambda r: r["price"])
    near = [r for r in book if abs(r["price"] - iep) <= max(5.0, 0.002 * iep)]
    lines = [f"{symbol} pre-open (NSE, updated {t} IST): opening price {'FINAL' if final else 'INDICATIVE (not fixed yet: wait until the final price appears; about 09:09 on 15 and 16 Oct)'} = Rs {iep:,.1f}, {100*(iep/prev-1):+.2f}% vs previous close Rs {prev:,.1f}.",
             f"Orders waiting: {int(p['totalBuyQuantity']):,} to buy vs {int(p['totalSellQuantity']):,} to sell (shares); matched at the open: {int(p['finalQuantity']):,}.  Book near the price: " + "; ".join(f"{r['price']:.1f}: buy {r['buyQty']:,} / sell {r['sellQty']:,}" for r in near)]
    if final:
        lines.append("This is the official opening price (to within a tick or two): not a forecast.")
    return "\n".join(lines)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--symbol", default="BSE"); ap.add_argument("--nosave", action="store_true"); a = ap.parse_args()
    s = fetch(a.symbol); print(words(s, a.symbol))
    if not a.nosave:
        day = dt.datetime.strptime(s["pre"]["lastUpdateTime"][:11], "%d-%b-%Y").strftime("%Y-%m-%d")
        Path("results/preopen").mkdir(parents=True, exist_ok=True)
        with open(f"results/preopen/{a.symbol}_{day}.jsonl", "a") as f:
            f.write(json.dumps({**s, "fetched_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}) + "\n")

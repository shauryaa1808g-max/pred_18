"""NSE pre-open call auction for BSE: the OPENING PRICE as the exchange itself computes it, readable from 09:00 and final at about 09:09 IST (trading starts 09:15).

  python3 src/preopen.py                       # fetch now, print in plain words, append the snapshot to results/preopen/<symbol>_<date>.jsonl
  python3 src/preopen.py --symbol CDSL
  python3 src/preopen.py --wait-final 240      # keep reading (every ~15 s, at most 240 s) until the price is FINAL, today's page is missing (holiday) or time is up

The indicative equilibrium price (IEP) moves while orders are entered and is fixed when the order-entry period closes at a system-random moment.  Since 7 Sep 2026 (NSE circular NSE/CMTR/74969, effective
7 Sep 2026): entry 09:00-09:05 limit and market orders, 09:05-09:10 limit orders only, random close in the last two minutes (so anywhere from 09:08:00 to 09:10:00), then matching and opening-price
determination, buffer to 09:15.  Seen live: 15 Oct final stamped 09:09:34, 16 Oct 09:09:00 (a 09:08:34 snapshot still had finalPrice 0).  The tool therefore calls the price FINAL only when NSE's finalPrice
and finalQuantity fields are filled on today's page, never by the clock.  NSE uses it as the official open, so from then on this is
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

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
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


def status(s: dict, now: dt.datetime | None = None) -> str:
    """FINAL | INDICATIVE | STALE | NO_PRICE for a snapshot returned by fetch().
    STALE: the page is not from today (holiday, weekend, or the new session has not started: the endpoint keeps the last session's page).
    FINAL: finalPrice and finalQuantity are filled (NSE fills them only once the auction has matched; 16 Oct: IEP 3,450 at 09:08:34 with finalPrice 0, finalPrice 3,450 stamped 09:09:00)
           and the stamp is not before 09:08:00 (the earliest possible random close).
    NO_PRICE: after 09:15 no price was discovered (the open is then the first trade of the normal market).  Any parsing problem gives INDICATIVE, never FINAL."""
    try:
        p = s["pre"]; t = p["lastUpdateTime"]; now = now or dt.datetime.now(IST)
        if dt.datetime.strptime(t[:11], "%d-%b-%Y").date() != now.date():
            return "STALE"
        fin = float(p.get("finalPrice") or 0); q = float(p.get("finalQuantity") or 0)
        if fin > 0 and q > 0 and t[-8:] >= "09:08:00":
            return "FINAL"
        if fin == 0 and now.strftime("%H:%M") >= "09:15":
            return "NO_PRICE"
        return "INDICATIVE"
    except Exception:                                                      # noqa: BLE001
        return "INDICATIVE"


def words(s: dict, symbol: str = "BSE", now: dt.datetime | None = None) -> str:
    m, p = s["meta"], s["pre"]; iep = float(p["IEP"]); prev = float(p["prevClose"])
    t = p["lastUpdateTime"]; hhmmss = t[-8:]
    st = status(s, now); final = st == "FINAL"
    if final: iep = float(p["finalPrice"])
    if st == "STALE":
        return f"{symbol} pre-open: no page for today yet (NSE still shows the page of {t[:11]}): holiday or weekend, or today's pre-open has not started (it opens 09:00).  Nothing to read."
    book = sorted(p["preopen"], key=lambda r: r["price"])
    near = [r for r in book if abs(r["price"] - iep) <= max(5.0, 0.002 * iep)]
    lines = [f"{symbol} pre-open (NSE, updated {t} IST): opening price {'FINAL' if final else ('NOT DISCOVERED (no pre-open match: the open will be the first trade)' if st == 'NO_PRICE' else 'INDICATIVE (not fixed yet: NSE closes order entry at a random moment between 09:08 and 09:10; wait until the final price appears)')} = Rs {iep:,.1f}, {100*(iep/prev-1):+.2f}% vs previous close Rs {prev:,.1f}.",
             f"Orders waiting: {int(p['totalBuyQuantity']):,} to buy vs {int(p['totalSellQuantity']):,} to sell (shares); matched at the open: {int(p['finalQuantity']):,}.  Book near the price: " + "; ".join(f"{r['price']:.1f}: buy {r['buyQty']:,} / sell {r['sellQty']:,}" for r in near)]
    if final:
        lines.append("This is the official opening price (to within a tick or two): not a forecast.")
    return "\n".join(lines)


def save_snapshot(s: dict, symbol: str, st: str, t_req: dt.datetime) -> None:
    """Append one snapshot (with its status, request time and the lag between the clock and NSE's own stamp) to results/preopen/<symbol>_<date>.jsonl.  Stale pages are never saved."""
    if st == "STALE":
        return
    day = dt.datetime.strptime(s["pre"]["lastUpdateTime"][:11], "%d-%b-%Y").strftime("%Y-%m-%d")
    stamp = None
    try: stamp = dt.datetime.strptime(s["snapshot_timestamp"], "%d-%b-%Y %H:%M:%S").replace(tzinfo=IST)
    except Exception: pass                                                 # noqa: BLE001
    Path("results/preopen").mkdir(parents=True, exist_ok=True)
    with open(f"results/preopen/{symbol}_{day}.jsonl", "a") as f:
        f.write(json.dumps({**s, "status": st, "fetched_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "request_start_ist": t_req.isoformat(timespec="seconds"),
                            "feed_lag_s": None if stamp is None else round((t_req - stamp).total_seconds())}) + "\n")


def rebuild_readings() -> None:
    """Refresh results/readings/readings.csv (every reading given to the user); never lets a CSV problem hide the pre-open price."""
    try:
        import readings_csv as RC
        RC.rebuild()
    except Exception as e:                                                 # noqa: BLE001
        print(f"(readings CSV not refreshed: {type(e).__name__}: {e})")


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--symbol", default="BSE"); ap.add_argument("--nosave", action="store_true")
    ap.add_argument("--wait-final", type=int, default=0, metavar="SECONDS", help="poll every ~15 s until FINAL/STALE/NO_PRICE or SECONDS have passed")
    a = ap.parse_args()
    t0 = time.time()
    while True:
        t_req = dt.datetime.now(IST)
        s = fetch(a.symbol); st = status(s, t_req)
        if st != "INDICATIVE" or time.time() - t0 + 15 > a.wait_final:
            break
        time.sleep(15)
    print(words(s, a.symbol, t_req))
    if a.nosave or st == "STALE":
        return
    save_snapshot(s, a.symbol, st, t_req)
    rebuild_readings()


if __name__ == "__main__":
    main()

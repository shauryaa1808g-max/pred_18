"""Capital-market peers' move since the previous close, next to BSE's own: the eighth column of the hour-by-hour table (CONTEXT ONLY: no forecast or pin-point uses it).
Forward test H, frozen definitions: research/hl/H_peer_forward.md (read section 0 there first).

  python3 src/peers_live.py                      # the peer snapshot for right now against BSE's price now (prints, saves nothing)
  python3 src/peers_live.py --asof 13:12         # TEST/INSPECTION ONLY: the same as of 13:12 today (Yahoo 1-minute bars that started before 13:12); never logged, never a reading

Definitions (all moves are 100 x ln(price / previous close), i.e. percent to within 0.04 point at these sizes):
  peer price = close of the last Yahoo 1-minute bar that STARTED before the reading's minute (the same rule as BSE's own price); previous close = Yahoo `chartPreviousClose` of the same request;
  a peer is dropped at a reading if it has no bar, its last bar is more than 10 minutes older than the reading, or |move| > 15% (corporate action or bad print: the same rule as study G);
  basket P (primary) = CDSL, MCX, MOTILALOFS, IEX (PEERS of src/hl_analog.py), valid with >= 3 of 4;  basket S (secondary) = ANGELONE, CDSL, MCX, valid with >= 2 of 3;
  basket move M = equal-weight mean of the available peer moves;  BSE move b = 100 x ln(price now / official previous close);  gap G = M - b in points (G > 0: the peers are doing better than BSE).
  Nifty 50 and Bank Nifty are fetched and shown for context and never tested.
Data: Yahoo chart API (unofficial); one request per symbol (seven in all), run in parallel.  A failure of any request is shown in the cell and never blocks the table.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import json
import math
import subprocess

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
BASKET_P = ("CDSL", "MCX", "MOTILALOFS", "IEX")
BASKET_S = ("ANGELONE", "CDSL", "MCX")
MIN_P, MIN_S = 3, 2
INDICES = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK"}
STALE_MIN = 10
MAX_ABS_MOVE_PCT = 15.0


def ysym(sym: str) -> str:
    return INDICES.get(sym, sym + ".NS")


def fetch(sym: str) -> dict:
    """Yahoo 1-minute chart for one symbol (today's session). Raises on failure."""
    last = None
    for host in ("query2", "query1"):
        url = f"https://{host}.finance.yahoo.com/v8/finance/chart/{ysym(sym)}?interval=1m&range=1d"
        out = subprocess.run(["curl", "-sS", "-m", "20", "-A", "Mozilla/5.0", url], capture_output=True, text=True)
        try:
            return json.loads(out.stdout)["chart"]["result"][0]
        except Exception as e:                                             # noqa: BLE001
            last = e
    raise RuntimeError(f"{sym}: {type(last).__name__}")


def fetch_all(symbols) -> dict:
    res = {}
    with cf.ThreadPoolExecutor(max_workers=len(symbols)) as ex:
        futs = {s: ex.submit(fetch, s) for s in symbols}
        for s, f in futs.items():
            try:
                res[s] = f.result()
            except Exception as e:                                         # noqa: BLE001
                res[s] = e
    return res


def one(res, T: dt.datetime) -> dict:
    """Move of one symbol at reading minute T (bars that started before T only)."""
    if isinstance(res, Exception):
        return {"status": "fetch_failed", "error": str(res)}
    try:
        pc = float(res["meta"]["chartPreviousClose"])
        ts, cl = res["timestamp"], res["indicators"]["quote"][0]["close"]
    except Exception as e:                                                 # noqa: BLE001
        return {"status": "bad_response", "error": f"{type(e).__name__}"}
    bars = [(dt.datetime.fromtimestamp(t, IST), c) for t, c in zip(ts, cl) if c is not None]
    bars = [(t, c) for t, c in bars if t < T and t.date() == T.date()]
    if not bars:
        return {"status": "no_bar", "prev_close": pc}
    t, c = bars[-1]
    mv = 100.0 * math.log(c / pc)
    d = {"prev_close": round(pc, 2), "price": round(float(c), 2), "bar_start": t.strftime("%H:%M"), "move_pct": round(mv, 3)}
    if (T - t).total_seconds() > STALE_MIN * 60:
        d["status"] = "stale"
    elif abs(mv) > MAX_ABS_MOVE_PCT:
        d["status"] = "outlier"
    else:
        d["status"] = "ok"
    return d


def basket(syms: dict, names, need: int) -> dict:
    ok = [(n, syms[n]["move_pct"]) for n in names if syms.get(n, {}).get("status") == "ok"]
    if len(ok) < need:
        return {"valid": False, "n_ok": len(ok), "n_of": len(names), "move_pct": None}
    return {"valid": True, "n_ok": len(ok), "n_of": len(names), "move_pct": round(sum(m for _, m in ok) / len(ok), 3)}


def snapshot(T: dt.datetime, bse_price: float, bse_prev_close: float, raw: dict | None = None) -> dict:
    """Peer snapshot for the reading minute T. `raw` (symbol -> Yahoo result) may be passed for tests; otherwise the seven requests are made now."""
    names = sorted(set(BASKET_P) | set(BASKET_S) | set(INDICES))
    raw = raw if raw is not None else fetch_all(names)
    syms = {n: one(raw[n], T) for n in names}
    b = 100.0 * math.log(bse_price / bse_prev_close)
    P, S = basket(syms, BASKET_P, MIN_P), basket(syms, BASKET_S, MIN_S)
    gap = lambda B: None if not B["valid"] else round(B["move_pct"] - b, 3)             # noqa: E731
    return {"T": T.strftime("%H:%M"), "bse_move_pct": round(b, 3), "symbols": syms, "P": P, "S": S, "gap_P_pp": gap(P), "gap_S_pp": gap(S),
            "source": "Yahoo chart API 1-minute bars (unofficial); definitions: research/hl/H_peer_forward.md section 0.1"}


def words(sn: dict) -> str:
    """The cell text of the eighth column."""
    if "error" in sn:
        return f"n/a: peers could not be read ({sn['error']})"
    P = sn["P"]
    if not P["valid"]:
        bad = ", ".join(f"{n} {sn['symbols'][n]['status']}" for n in BASKET_P if sn["symbols"][n]["status"] != "ok")
        return f"n/a: only {P['n_ok']} of {P['n_of']} peers had a current price ({bad})"
    parts = ", ".join(f"{n} {sn['symbols'][n]['move_pct']:+.2f}" if sn["symbols"][n]["status"] == "ok" else f"{n} n/a" for n in BASKET_P)
    nf = sn["symbols"]["NIFTY"]
    nifty = f"; Nifty {nf['move_pct']:+.2f}%" if nf.get("status") == "ok" else ""
    return f"peers average {P['move_pct']:+.2f}% ({parts}) vs BSE {sn['bse_move_pct']:+.2f}%: peers minus BSE {sn['gap_P_pp']:+.2f} points{nifty}; moves since the previous close; context only, not a forecast"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--asof", default=None)
    a = ap.parse_args()
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import live_highlow as LH
    import live_nowcast as LN
    now = dt.datetime.now(IST)
    df, _ = LH.get_bars(save=False)
    sdate = df.date.iloc[-1]
    day = df[df.date == sdate]
    T = dt.datetime.fromisoformat(f"{sdate}T{a.asof}:00").replace(tzinfo=IST) if a.asof else now.replace(second=0, microsecond=0)
    d1 = day[day.t < T]
    P = float(d1.close.iloc[-1])
    sn = snapshot(T, P, LN.prev_close_before(sdate))
    print(json.dumps(sn, indent=1)); print(); print(words(sn))

"""Daily scoreboard for NSE:BSE: commit a next-session forecast BEFORE the open, score it AFTER the close, keep a running tally of what it is worth.

  python3 src/scoreboard.py issue [--date 2026-10-16]   # run after the US close (~01:30 IST) and before 09:15 IST; commit the entry before the open
  python3 src/scoreboard.py score [--date 2026-10-16]   # run after NSE publishes the official bhavcopy (~16:34 IST)
  python3 src/scoreboard.py report                      # running totals in plain words

What an entry holds (all decided before the open, from past data only):
  * open and close distributions (same pre-registered volatility models as the main forecast; centre = previous official close, no drift claimed)
  * a direction LEAN for the close and for open->close from last night's S&P 500 move plus BSE's own last two days (expanding walk-forward OLS; the check in src/direction_check.py found
    about 55% right on 8 years, unstable by year, roughly zero after costs) -- a lean, not a prediction
  * two PAPER-TRADE rules fixed now, nothing else will be added: PT1 = trade open->close in the lean's direction every day; PT2 = same, only when the lean is in its strongest 20%.
    Round-trip cost 0.10% is charged.  Paper only: no real money is implied.
The scoreboard compares everything with the dumb benchmark 'unchanged' (open = close = previous close).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

import models as P
from common import EPS, GRID, targets
from forecast_live import SELECT, live_sigma, quantiles
from official_bars import ensure_bars, load_bse_ext

DIR = Path("results/scoreboard"); ENT = DIR / "entries"; OUT = DIR / "outcomes"; CSV = DIR / "scoreboard.csv"
COST = 0.0010
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
LEAN_MIN_TRAIN = 500


def git(*a) -> str:
    return subprocess.run(["git", *a], capture_output=True, text=True).stdout.strip()


def sp_returns() -> pd.Series:
    """daily S&P 500 log returns indexed by US session date: FRED history extended with Yahoo ^GSPC (needed for the most recent sessions)."""
    f = pd.read_csv("data/raw/macro/SP500.csv"); f.columns = ["date", "v"]; f["v"] = pd.to_numeric(f["v"], errors="coerce"); f["date"] = pd.to_datetime(f["date"]); s = f.dropna().set_index("date").v
    try:
        out = subprocess.run(["curl", "-sS", "-m", "30", "-A", "Mozilla/5.0", "https://query2.finance.yahoo.com/v8/finance/chart/%5EGSPC?interval=1d&range=3mo"], capture_output=True, text=True)
        r = json.loads(out.stdout)["chart"]["result"][0]
        y = pd.Series(r["indicators"]["quote"][0]["close"], index=pd.to_datetime(r["timestamp"], unit="s", utc=True).tz_convert("America/New_York").tz_localize(None).normalize()).dropna()
        y = y[~y.index.duplicated(keep="last")]
        s = pd.concat([s, y[y.index > s.index[-1]]])
    except Exception as e:                                             # noqa: BLE001
        print("WARNING: could not extend the S&P series from Yahoo:", e)
    return np.log(s).diff().dropna()


def prior_us(spr: pd.Series, day: pd.Timestamp, now_ist: dt.datetime | None = None) -> tuple[float, pd.Timestamp]:
    """latest completed US session dated strictly before the Indian session date (the alignment validated in research/v2/03)."""
    j = spr.index.searchsorted(day) - 1
    return float(spr.iloc[j]), spr.index[j]


def lean_models(d: pd.DataFrame, spr: pd.Series) -> dict:
    t = targets(d)
    sp = pd.Series({k: spr.iloc[spr.index.searchsorted(k) - 1] if spr.index.searchsorted(k) > 0 else np.nan for k in d.index})
    df = pd.DataFrame({"I": t["I"], "R": t["R"], "sp": sp, "pI": t["I"].shift(1), "pR": t["R"].shift(1)}).dropna()
    cols = ["sp", "pI", "pR"]; X = df[cols].values
    def fit(y, i): return np.linalg.lstsq(np.c_[np.ones(i), X[:i]], df[y].values[:i], rcond=None)[0]
    wf_I = np.array([np.r_[1, X[i]] @ fit("I", i) for i in range(max(LEAN_MIN_TRAIN, len(df) - 500), len(df))])
    return {"df": df, "coef_I": fit("I", len(df)), "coef_R": fit("R", len(df)), "thr80_abs_I": float(np.quantile(np.abs(wf_I), 0.8)), "last_I": float(t["I"].iloc[-1]), "last_R": float(t["R"].iloc[-1])}


def issue(target: pd.Timestamp, dry: bool = False) -> dict:
    ensure_bars(); d = load_bse_ext()
    if d.index[-1] >= target:
        raise SystemExit(f"data already contains {target.date()}; issue entries before the session")
    t = targets(d); n = len(d); P0 = float(d["close"].iloc[-1])
    x = {k: t[k].values for k in ("R", "G")}; v = {"R": t["v"].values, "G": np.clip(t["G"].values ** 2, EPS, None)}
    q = {}
    for tg in ("G", "R"):
        s = live_sigma(x[tg], v[tg], SELECT[tg]); qq = quantiles(x[tg], s, n)
        q[tg] = {"sigma_pct": float(100 * s[n]), "price": {f"q{g:g}": round(P0 * float(np.exp(z)), 2) for g, z in zip(GRID, qq)}}
    spr = sp_returns(); sp_now, sp_date = prior_us(spr, target)
    lm = lean_models(d, spr); xnew = np.r_[1, sp_now, lm["last_I"], lm["last_R"]]
    pred_I = float(xnew @ lm["coef_I"]); pred_R = float(xnew @ lm["coef_R"])
    pt2_on = abs(pred_I) >= lm["thr80_abs_I"]
    entry = {"target_session": str(target.date()), "made_at_ist": dt.datetime.now(IST).isoformat(timespec="seconds"), "data_through": str(d.index[-1].date()), "reference_price": P0,
             "open": q["G"], "close": q["R"], "unchanged_benchmark": P0,
             "lean": {"us_session_used": str(sp_date.date()), "sp500_return_pct": 100 * sp_now, "pred_close_to_close_pct": 100 * pred_R, "pred_open_to_close_pct": 100 * pred_I,
                      "direction_close": "up" if pred_R > 0 else "down", "direction_open_to_close": "up" if pred_I > 0 else "down", "strongest_20pct_threshold_abs_pct": 100 * lm["thr80_abs_I"],
                      "statement": "a lean, not a prediction: about 55% right on 8 years, unstable by year, about zero profit after costs"},
             "paper_trades": {"PT1_every_day": {"side": "long" if pred_I > 0 else "short", "enter": "official open", "exit": "official close", "round_trip_cost_pct": 100 * COST},
                              "PT2_strongest_20pct_only": {"side": ("long" if pred_I > 0 else "short") if pt2_on else "none", "enter": "official open", "exit": "official close", "round_trip_cost_pct": 100 * COST}},
             "code_commit": git("rev-parse", "HEAD"), "code_tree_dirty": bool(git("status", "--porcelain", "--untracked-files=no"))}
    if dry:
        print(words(entry)); print("\n(dry run: nothing written)"); return entry
    ENT.mkdir(parents=True, exist_ok=True)
    path = ENT / f"{target.date()}.json"
    if path.exists():
        raise SystemExit(f"{path} already exists: entries are never rewritten")
    path.write_text(json.dumps(entry, indent=1))
    print(words(entry)); print(f"\nwrote {path}  -> COMMIT IT BEFORE 09:15 IST so the commit time proves it was made before the open")
    return entry


def words(e: dict) -> str:
    o, c, l = e["open"]["price"], e["close"]["price"], e["lean"]
    return (f"{e['target_session']}  (made {e['made_at_ist'][11:16]} IST; reference = previous official close Rs {e['reference_price']:,.1f})\n"
            f"  OPEN : about Rs {o['q0.5']:,.0f}; half the time between Rs {o['q0.25']:,.0f} and {o['q0.75']:,.0f}; 9 in 10 between Rs {o['q0.05']:,.0f} and {o['q0.95']:,.0f}\n"
            f"  CLOSE: about Rs {c['q0.5']:,.0f}; half the time between Rs {c['q0.25']:,.0f} and {c['q0.75']:,.0f}; 9 in 10 between Rs {c['q0.05']:,.0f} and {c['q0.95']:,.0f}\n"
            f"  LEAN : {l['direction_close']} for the close (model says {l['pred_close_to_close_pct']:+.2f}%), {l['direction_open_to_close']} open->close ({l['pred_open_to_close_pct']:+.2f}%); "
            f"S&P {l['us_session_used']}: {l['sp500_return_pct']:+.2f}%.  {l['statement']}.\n"
            f"  PAPER: PT1 {e['paper_trades']['PT1_every_day']['side']} at the open;  PT2 {e['paper_trades']['PT2_strongest_20pct_only']['side']} at the open (only the strongest 20% of leans).")


def score(day: pd.Timestamp) -> dict:
    ensure_bars(); d = load_bse_ext()
    if day not in d.index:
        raise SystemExit(f"official bar for {day.date()} not available yet (NSE publishes about 16:34 IST)")
    e = json.loads((ENT / f"{day.date()}.json").read_text()); r = d.loc[day]; P0 = e["reference_price"]
    op, cl = float(r["open"]), float(r["close"]); o, c = e["open"]["price"], e["close"]["price"]
    inside = lambda q, y, a, b: bool(q[a] <= y <= q[b])                 # noqa: E731
    res = {"date": str(day.date()), "open": op, "close": cl, "prev_close": P0, "open_median": o["q0.5"], "close_median": c["q0.5"],
           "open_miss_rs": op - o["q0.5"], "close_miss_rs": cl - c["q0.5"], "open_miss_unchanged_rs": op - P0, "close_miss_unchanged_rs": cl - P0,
           "open_in50": inside(o, op, "q0.25", "q0.75"), "open_in90": inside(o, op, "q0.05", "q0.95"), "close_in50": inside(c, cl, "q0.25", "q0.75"), "close_in90": inside(c, cl, "q0.05", "q0.95"),
           "lean_close": e["lean"]["direction_close"], "close_return_pct": 100 * np.log(cl / P0), "lean_hit": bool((cl > P0) == (e["lean"]["direction_close"] == "up")) if cl != P0 else None,
           "open_to_close_pct": 100 * np.log(cl / op)}
    for k in ("PT1_every_day", "PT2_strongest_20pct_only"):
        side = e["paper_trades"][k]["side"]; pnl = np.nan
        if side != "none":
            ret = np.log(cl / op) * (1 if side == "long" else -1); pnl = 100 * (np.exp(ret) - 1 - COST)
        res[k.split("_")[0] + "_net_pct"] = None if np.isnan(pnl) else float(pnl); res[k.split("_")[0] + "_side"] = side
    OUT.mkdir(parents=True, exist_ok=True); (OUT / f"{day.date()}.json").write_text(json.dumps(res, indent=1))
    old = pd.read_csv(CSV) if CSV.exists() else pd.DataFrame()
    old = old[old.date != res["date"]] if len(old) else old
    pd.concat([old, pd.DataFrame([res])]).sort_values("date").to_csv(CSV, index=False)
    print(json.dumps(res, indent=1)); return res


def report() -> None:
    if not CSV.exists():
        print("no scored days yet"); return
    s = pd.read_csv(CSV); n = len(s)
    mae = lambda a: float(np.mean(np.abs(a)))                          # noqa: E731
    print(f"SCOREBOARD  ({n} scored session{'s' if n != 1 else ''}: {s.date.iloc[0]} to {s.date.iloc[-1]})")
    print(f"  open : my typical miss Rs {mae(s.open_miss_rs):.1f}  vs 'unchanged' Rs {mae(s.open_miss_unchanged_rs):.1f};  inside my 50% band {100*s.open_in50.mean():.0f}%, 90% band {100*s.open_in90.mean():.0f}%")
    print(f"  close: my typical miss Rs {mae(s.close_miss_rs):.1f}  vs 'unchanged' Rs {mae(s.close_miss_unchanged_rs):.1f};  inside my 50% band {100*s.close_in50.mean():.0f}%, 90% band {100*s.close_in90.mean():.0f}%")
    h = s.lean_hit.dropna().astype(bool)
    if len(h):
        lo, hi = stats.beta.ppf([0.025, 0.975], [h.sum() + 1e-9, h.sum() + 1], [len(h) - h.sum() + 1, len(h) - h.sum() + 1e-9]) if 0 < h.sum() < len(h) else (np.nan, np.nan)
        print(f"  direction lean right {int(h.sum())} of {len(h)} ({100*h.mean():.0f}%; 95% range about {100*lo:.0f}-{100*hi:.0f}%; a coin flip is 50%; wait for 30+ sessions before reading anything into it)")
    for k, lab in (("PT1", "PT1 every day"), ("PT2", "PT2 strongest 20%")):
        v = s[k + "_net_pct"].dropna()
        if len(v):
            print(f"  paper {lab}: {len(v)} trades, average {v.mean():+.2f}% per trade after costs, wins {100*(v>0).mean():.0f}%, running total {v.sum():+.2f}%")
    print("  (paper only; 0.10% round-trip cost charged; the earlier 8-year check suggested roughly zero edge after costs)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["issue", "score", "report"]); ap.add_argument("--date", default=None); ap.add_argument("--dry", action="store_true"); a = ap.parse_args()
    if a.cmd == "report":
        report()
    else:
        day = pd.Timestamp(a.date) if a.date else pd.Timestamp(dt.datetime.now(IST).date()) + pd.Timedelta(days=1 if a.cmd == "issue" else 0)
        issue(day, a.dry) if a.cmd == "issue" else (score(day), report())

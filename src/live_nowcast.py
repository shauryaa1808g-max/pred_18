"""Live close nowcast for NSE:BSE: where will today's OFFICIAL close (closing-auction price) land, given the price right now?

Idea (descriptive, calibrated on ~39 post-closing-auction sessions of 15-minute bars): from the current time to the close, price moves like a random walk with the
time-of-day variance profile seen in those sessions, scaled up or down by how wild today has been so far.  Centre = last traded price (no drift claimed).
This is a nowcast, not a next-day forecast: it gets tight only because the day is mostly over.

Usage (repo root):
  python3 src/live_nowcast.py                 # fetch Yahoo 1-minute bars now, print plain-words nowcast, log it
  python3 src/live_nowcast.py --backtest      # leave-one-session-out calibration of the method
  python3 src/live_nowcast.py --refresh       # add newly completed sessions (from Yahoo 1-minute bars) to data/processed/intraday_extra_15m.csv
Data source: Yahoo chart API (unofficial, near-real-time).  The official close is published by NSE about 16:34 IST.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
NB = 25                                   # 15-minute slots 09:15 ... 15:15 (slot 24 = 15:15-15:30, contains the closing auction)
W_SCALE = 0.0                             # weight on "today's volatility so far": the leave-one-session-out test (--backtest) found no gain from it (w=0: 90% bands cover 90.0%; w=0.5: 88.9%; w=1: 86.0%)
UNION, EXTRA = "data/processed/intraday_union_15m.csv", "data/processed/intraday_extra_15m.csv"
LOG = "results/nowcast_log.jsonl"


# ------------------------------------------------------------------ data
def yahoo_1m(rng: str = "1d") -> dict:
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/BSE.NS?interval=1m&range={rng}"
    out = subprocess.run(["curl", "-sS", "-m", "30", "-A", "Mozilla/5.0", url], capture_output=True, text=True)
    if out.returncode != 0 or not out.stdout.startswith("{"):
        url = url.replace("query2", "query1")
        out = subprocess.run(["curl", "-sS", "-m", "30", "-A", "Mozilla/5.0", url], capture_output=True, text=True)
    return json.loads(out.stdout)["chart"]["result"][0]


def rows_1m(res: dict) -> pd.DataFrame:
    q = res["indicators"]["quote"][0]
    df = pd.DataFrame({"t": pd.to_datetime(res["timestamp"], unit="s", utc=True).tz_convert(IST), "open": q["open"], "high": q["high"], "low": q["low"], "close": q["close"], "volume": q["volume"]}).dropna(subset=["close"])
    df["date"] = df.t.dt.strftime("%Y-%m-%d")
    df["slot"] = ((df.t.dt.hour * 60 + df.t.dt.minute - (9 * 60 + 15)) // 15).astype(int)
    return df[(df.slot >= 0) & (df.slot < NB)]


def to_15m(df1: pd.DataFrame) -> pd.DataFrame:
    g = df1.groupby(["date", "slot"]).agg(open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"), volume=("volume", "sum")).reset_index()
    g["time"] = [f"{9 + (15 + 15 * s) // 60:02d}:{(15 + 15 * s) % 60:02d}" for s in g.slot]
    return g[["date", "time", "open", "high", "low", "close", "volume"]]


def load_history() -> list[dict]:
    frames = [pd.read_csv(UNION)[["date", "time", "open", "high", "low", "close", "volume"]]]
    if Path(EXTRA).exists():
        frames.append(pd.read_csv(EXTRA)[["date", "time", "open", "high", "low", "close", "volume"]])
    u = pd.concat(frames).drop_duplicates(["date", "time"], keep="first")
    sessions = []
    for date, g in u.groupby("date"):
        g = g.copy(); g["slot"] = [(int(t[:2]) * 60 + int(t[3:5]) - 555) // 15 for t in g.time.astype(str)]
        if len(g) < 24:
            continue
        c = np.full(NB, np.nan)
        for s, cl in zip(g.slot, g.close): c[s] = cl
        c = pd.Series(c).ffill().values                  # sessions without a 15:15 bar: the closing print sits in the 15:00 bar
        r = np.diff(np.log(np.r_[g.open.iloc[0], c]))
        sessions.append({"date": date, "r": r, "c": c, "close": float(c[-1])})
    return sessions


# ------------------------------------------------------------------ method
def profile(sessions: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    """mean per-slot variance E[r_k^2] and cumulative 'so far' variance for m completed slots."""
    R2 = np.array([s["r"] ** 2 for s in sessions])
    ev = R2.mean(axis=0)
    return ev, np.r_[0.0, np.cumsum(ev)]


def nowcast_sigma(ev: np.ndarray, cum: np.ndarray, m: int, frac: float, v_sofar: float, w: float = W_SCALE) -> tuple[float, float]:
    """sigma of ln(official close / price now) for m completed slots plus fraction `frac` of slot m already elapsed."""
    rem = ((1 - frac) * ev[m] + ev[m + 1:].sum()) if m < NB else 0.0
    ratio = v_sofar / cum[m] if cum[m] > 0 else 1.0
    scale2 = float(np.clip((1 - w) + w * ratio, 0.4, 4.0))
    return float(np.sqrt(scale2 * rem)), scale2


def backtest(w: float = W_SCALE) -> dict:
    S = load_history(); z, y_abs, rows = [], [], []
    for j, sj in enumerate(S):
        ev, cum = profile(S[:j] + S[j + 1:])
        for m in range(2, 24):
            sig, _ = nowcast_sigma(ev, cum, m, 0.0, float((sj["r"][:m] ** 2).sum()), w)
            y = np.log(sj["close"] / sj["c"][m - 1])
            z.append(y / sig); y_abs.append(abs(y)); rows.append((sj["date"], m, y, sig))
    z = np.array(z)
    return {"w": w, "n_sessions": len(S), "n_points": len(z), "cover50_gauss": float((np.abs(z) < 0.674).mean()), "cover90_gauss": float((np.abs(z) < 1.645).mean()), "cover95_gauss": float((np.abs(z) < 1.96).mean()),
            "mean_abs_z": float(np.abs(z).mean()), "mean_abs_miss_pct": float(100 * np.mean(y_abs)), "z_quantiles": {str(q): float(np.quantile(z, q)) for q in (0.025, 0.05, 0.25, 0.5, 0.75, 0.95, 0.975)}, "rows": rows}


# ------------------------------------------------------------------ live
def prev_close_official() -> float:
    d = pd.read_csv("data/processed/bse_daily.csv", index_col=0, parse_dates=True)
    extra = Path("data/processed/bse_daily_extra.csv")
    if extra.exists():
        e = pd.read_csv(extra, index_col=0, parse_dates=True); d = pd.concat([d, e[~e.index.isin(d.index)]])
    return float(d["close"].iloc[-1])


def run_live(save: bool = True, asof: str | None = None) -> dict:
    res = yahoo_1m("1d"); meta = res["meta"]; df1 = rows_1m(res)
    today = df1.date.iloc[-1]; df1 = df1[df1.date == today]
    if asof:                                            # replay: pretend it is HH:MM (uses only bars up to then)
        df1 = df1[df1.t.dt.strftime('%H:%M') <= asof]
    now = df1.t.iloc[-1]; price = float(df1.close.iloc[-1])
    mins = now.hour * 60 + now.minute + now.second / 60 - 555
    m, frac = int(min(mins // 15, NB)), float((mins % 15) / 15) if mins < NB * 15 else 0.0
    S = load_history(); ev, cum = profile([s for s in S if s["date"] != today])
    o0 = float(df1.open.iloc[0])
    slots = df1.groupby("slot").close.last()
    cs = pd.Series(np.nan, index=range(NB)); cs.loc[slots.index] = slots.values; cs = cs.ffill()
    rr = np.diff(np.log(np.r_[o0, cs.values[:max(m, 1)]])) if m >= 1 else np.array([0.0])
    v_sofar = float((rr[:m] ** 2).sum()) if m >= 1 else 0.0
    sig, scale2 = nowcast_sigma(ev, cum, m, frac, v_sofar)
    bt = backtest(); zq = bt["z_quantiles"]
    q = {k: price * float(np.exp(zq[k] * sig)) for k in zq}
    pc = prev_close_official() if Path("data/processed/bse_daily.csv").exists() else float(meta.get("previousClose", price))
    out = {"asof_ist": now.isoformat(timespec="seconds"), "source": "Yahoo chart API 1-minute bars (unofficial, near-real-time)", "price_now": price, "prev_official_close": pc, "change_vs_prev_close_pct": 100 * (price / pc - 1),
           "day_high_so_far": float(df1.high.max()), "day_low_so_far": float(df1.low.min()), "minutes_to_close": float(max(0, 15 * 60 + 30 - (now.hour * 60 + now.minute))),
           "sigma_remaining_pct": 100 * sig, "vol_scale_today_vs_typical": float(np.sqrt(scale2)), "indicative_close": price,
           "close_50": [q["0.25"], q["0.75"]], "close_90": [q["0.05"], q["0.95"]], "close_95": [q["0.025"], q["0.975"]], "typical_miss_rs": float(0.8 * sig * price),
           "calibration_note": f"leave-one-session-out on {bt['n_sessions']} sessions: Gaussian 50/90% bands cover {100*bt['cover50_gauss']:.0f}% / {100*bt['cover90_gauss']:.0f}% of checkpoints (descriptive; small sample, overlapping checkpoints)"}
    # tightening schedule if the price stayed where it is
    sched = []
    for k in (4, 8, 12, 16, 20, 22, 23):
        if k > m:
            s_k, _ = nowcast_sigma(ev, cum, k, 0.0, v_sofar * (cum[k] / cum[max(m, 1)]) if cum[max(m, 1)] > 0 else 0.0)
            sched.append({"at": f"{(555 + 15 * k) // 60:02d}:{(555 + 15 * k) % 60:02d}", "half_width_90_rs": float(1.645 * s_k * price)})
    out["tightening_schedule_if_price_unchanged"] = sched
    if save:
        Path("results").mkdir(exist_ok=True); Path("results/nowcast_latest.json").write_text(json.dumps(out, indent=1))
        with open(LOG, "a") as f: f.write(json.dumps({**out, "logged_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}) + "\n")
    return out


def words(o: dict) -> str:
    t = dt.datetime.fromisoformat(o["asof_ist"]).strftime("%H:%M")
    lines = [f"At {t} IST BSE is Rs {o['price_now']:,.1f} ({o['change_vs_prev_close_pct']:+.2f}% vs yesterday's close Rs {o['prev_official_close']:,.1f}); day range Rs {o['day_low_so_far']:,.1f} - {o['day_high_so_far']:,.1f}; {o['minutes_to_close']:.0f} min to the close.",
             f"Indicative close: Rs {o['indicative_close']:,.0f}.  Half the time between Rs {o['close_50'][0]:,.0f} and {o['close_50'][1]:,.0f}; nine times in ten between Rs {o['close_90'][0]:,.0f} and {o['close_90'][1]:,.0f}.  Typical miss about Rs {o['typical_miss_rs']:,.0f}.",
             f"Today has been {o['vol_scale_today_vs_typical']:.1f}x as wild as a typical day so far (not used in the estimate: it did not improve the test).  {o['calibration_note']}."]
    if o["tightening_schedule_if_price_unchanged"]:
        lines.append("If the price stays put, the 90% band half-width shrinks to: " + ", ".join(f"Rs {s['half_width_90_rs']:.0f} by {s['at']}" for s in o["tightening_schedule_if_price_unchanged"]))
    return "\n".join(lines)


def refresh() -> None:
    res = yahoo_1m("5d"); df1 = rows_1m(res); have = {s["date"] for s in load_history()}; new = []
    for date, g in df1.groupby("date"):
        if date in have or g.slot.nunique() < 24: continue
        new.append(to_15m(g))
    if new:
        out = pd.concat(new); old = pd.read_csv(EXTRA) if Path(EXTRA).exists() else None
        out = pd.concat([old, out]) if old is not None else out
        out.to_csv(EXTRA, index=False); print("added sessions:", sorted(out.date.unique())[-len(new):])
    else:
        print("no new complete sessions")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--backtest", action="store_true"); ap.add_argument("--refresh", action="store_true"); ap.add_argument("--nosave", action="store_true"); ap.add_argument("--asof", default=None, help="replay today as of HH:MM IST"); ap.add_argument("--replay", action="store_true", help="table of replays through today"); a = ap.parse_args()
    if a.refresh: refresh()
    elif a.backtest:
        for w in (0.0, 0.5, 1.0):
            b = backtest(w); b.pop("rows"); print(json.dumps(b, indent=1))
    elif a.replay:
        rows = []
        for hhmm in ('09:45', '10:30', '11:30', '12:30', '13:15', '13:45', '14:04', '14:30', '15:00'):
            o = run_live(False, hhmm); rows.append({'asof': hhmm, 'price_then': o['price_now'], 'close_50_lo': o['close_50'][0], 'close_50_hi': o['close_50'][1], 'close_90_lo': o['close_90'][0], 'close_90_hi': o['close_90'][1], 'typical_miss_rs': o['typical_miss_rs']})
        df = pd.DataFrame(rows); df.to_csv('results/nowcast_replay_latest.csv', index=False); print(df.round(1).to_string(index=False))
    else: print(words(run_live(not a.nosave, a.asof)))

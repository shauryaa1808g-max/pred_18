"""Hour-by-hour table for NSE:BSE in the user's fixed format (one row per time frame):

  time | precise close | close range at the end of the day | precise high of the next hour | precise low of the next hour |
  this hour's high vs the previous prediction of it | this hour's low vs the previous prediction of it
  plus, at 08:30 and 09:00 (before the open): the open range and the open pin-point.
  From 22 Oct 2026 a live row has an eighth column, "peers' move today vs BSE's" (src/peers_live.py): CONTEXT ONLY, pre-registered forward test H (research/hl/H_peer_forward.md);
  rows logged before that and replays (--asof) keep the seven columns exactly as before.

Usage (repo root):
  python3 src/hourly_table.py                  # the row for right now (Yahoo 1-minute bars, unofficial); logs the predictions to results/hourly_table_log.jsonl
  python3 src/hourly_table.py --vs 15:00       # compare 'this hour' with the table given at 15:00 instead of the latest previous one
  python3 src/hourly_table.py --asof 13:30     # replay today as of 13:30 (only 1-minute bars that started before 13:30)
  python3 src/hourly_table.py --pre-open       # the 08:30 / 09:00 row: open range and open pin-point (NSE pre-open price when it exists)
  python3 src/hourly_table.py --eval           # leave-one-session-out accuracy of the next-hour high/low model -> results/hourly_hl_eval.csv
  python3 src/hourly_table.py --report         # running accuracy of every scored prediction (results/hourly_table_scored.csv)

Method (descriptive, small sample; nothing here predicts direction):
  * close pin-point = the price now (no drift), range = src/live_nowcast.py's 50% / 90% range;
  * next-hour high / low: from the price now P and the typical size of price moves in the coming 60 minutes at this time of day
    (the variance profile of 15-minute bars since the closing auction, ~39 sessions), the high of the next hour is P * exp(z * sigma_window) where z comes from the
    pooled, standardised past excursions (filtered historical simulation).  The pin-point is the MEDIAN of that distribution.  The window is cut at 15:30.
  * 'this hour': ONLY the previous table given to the user (the latest live row logged before this one) is compared with what actually happened in ITS window (Yahoo 1-minute high / low; NSE's official figures can
    differ by a few rupees), 'so far only' while that window is not over. No replay and no recomputed prediction: with no earlier table the cell says so.
    Separately (bookkeeping for learning) every logged live prediction is scored once its own window is over (--score, results/hourly_table_scored.csv).
Known limits: 39 sessions; a few cells below are noisy; the leave-one-out table (--eval) says how big the typical miss is at each time of day.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import live_highlow as LH      # noqa: E402  (bars cache and fetch)
import live_nowcast as LN      # noqa: E402  (variance profile, close ranges)

IST = LN.IST
NB = LN.NB
TAUS = np.array([0.05, 0.25, 0.5, 0.75, 0.95])
LOG = "results/hourly_table_log.jsonl"
SCORED = "results/hourly_table_scored.csv"
EVAL = "results/hourly_hl_eval.csv"
WIN = 60                                  # minutes in 'the next hour'
OPEN_MIN, CLOSE_MIN = 9 * 60 + 15, 15 * 60 + 30


# ------------------------------------------------------------------ history (15-minute bars with highs and lows)
def load_sessions() -> list[dict]:
    cols = ["date", "time", "open", "high", "low", "close"]
    frames = [pd.read_csv(LN.UNION)[cols]]
    if Path(LN.EXTRA).exists():
        frames.append(pd.read_csv(LN.EXTRA)[cols])
    u = pd.concat(frames).drop_duplicates(["date", "time"], keep="first")
    out = []
    for date, g in u.groupby("date"):
        if len(g) < 24:
            continue
        g = g.assign(slot=[(int(t[:2]) * 60 + int(t[3:5]) - 555) // 15 for t in g.time.astype(str)]).sort_values("slot")
        o, h, l, c = (np.full(NB, np.nan) for _ in range(4))
        for s, op, hi, lo, cl in zip(g.slot, g.open, g.high, g.low, g.close):
            o[s], h[s], l[s], c[s] = op, hi, lo, cl
        has24 = not np.isnan(c[NB - 1])
        cf = pd.Series(c).ffill().values
        r = np.diff(np.log(np.r_[g.open.iloc[0], cf]))
        if not has24:
            r[NB - 1] = np.nan
        out.append({"date": date, "h": h, "l": l, "c": c, "cf": cf, "r": r, "has24": has24})
    return out


def excursions(S: list[dict], ev: np.ndarray) -> pd.DataFrame:
    """for every session and every checkpoint k = 1..23 (k completed 15-minute bars): P = close of bar k-1; the next hour = bars k..min(k+3, 24);
    Xh = ln(max high / P), Xl = ln(min low / P), sig = sqrt(sum of the profile variances of those bars)."""
    rows = []
    for s in S:
        for k in range(1, 24):
            end = min(k + 3, NB - 1)
            if np.isnan(s["h"][k:end + 1]).any() or np.isnan(s["cf"][k - 1]):
                continue
            P = s["cf"][k - 1]
            rows.append((s["date"], k, P, np.log(np.nanmax(s["h"][k:end + 1]) / P), np.log(np.nanmin(s["l"][k:end + 1]) / P), float(np.sqrt(ev[k:end + 1].sum()))))
    return pd.DataFrame(rows, columns=["date", "k", "P", "Xh", "Xl", "sig"])


def sigma_window(ev: np.ndarray, t0: int, t1: int) -> float:
    """sqrt of the profile variance between minute t0 and t1 (minutes since 09:15; per-minute variance = slot variance / 15)."""
    return float(np.sqrt(sum(ev[min(m // 15, NB - 1)] / 15 for m in range(t0, t1))))


def zpool(S: list[dict], ev: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ex = excursions(S, ev)
    return (ex.Xh / ex.sig).values, (ex.Xl / ex.sig).values


# ------------------------------------------------------------------ leave-one-session-out accuracy
def loo_eval(S: list[dict]) -> pd.DataFrame:
    res = []
    for i, s in enumerate(S):
        others = [x for j, x in enumerate(S) if j != i]
        ev, _ = LN.profile(others)
        zh, zl = zpool(others, ev)
        qh, ql = np.quantile(zh, TAUS), np.quantile(zl, TAUS)
        ex = excursions([s], ev)
        for _, r in ex.iterrows():
            P, k = r.P, int(r.k)
            hi_act, lo_act = P * np.exp(r.Xh), P * np.exp(r.Xl)
            ph, pl = P * np.exp(qh * r.sig), P * np.exp(ql * r.sig)
            res.append({"date": s["date"], "k": k, "P": P, "h_act": hi_act, "l_act": lo_act, "h_med": ph[2], "l_med": pl[2],
                        "h_in50": ph[1] <= hi_act <= ph[3], "h_in90": ph[0] <= hi_act <= ph[4], "l_in50": pl[1] <= lo_act <= pl[3], "l_in90": pl[0] <= lo_act <= pl[4]})
    d = pd.DataFrame(res)
    g = d.groupby("k")
    t = pd.DataFrame({"n_sessions": g.size(),
                      "high_miss_rs": g.apply(lambda x: (x.h_med - x.h_act).abs().mean()), "high_stays_miss_rs": g.apply(lambda x: (x.P - x.h_act).abs().mean()),
                      "low_miss_rs": g.apply(lambda x: (x.l_med - x.l_act).abs().mean()), "low_stays_miss_rs": g.apply(lambda x: (x.P - x.l_act).abs().mean()),
                      "high_cov50": g.h_in50.mean(), "high_cov90": g.h_in90.mean(), "low_cov50": g.l_in50.mean(), "low_cov90": g.l_in90.mean()}).reset_index()
    t.insert(1, "time", [f"{(555 + 15 * k) // 60:02d}:{(555 + 15 * k) % 60:02d}" for k in t.k])
    return t.round(3)


# ------------------------------------------------------------------ one row
def next_hour(P: float, tmin: int, ev: np.ndarray, zh: np.ndarray, zl: np.ndarray) -> dict | None:
    t1 = min(tmin + WIN, CLOSE_MIN - OPEN_MIN)
    if tmin >= CLOSE_MIN - OPEN_MIN or t1 <= tmin:
        return None
    sig = sigma_window(ev, tmin, t1)
    qh, ql = np.quantile(zh, TAUS) * sig, np.quantile(zl, TAUS) * sig
    f = lambda q: {str(t): round(float(P * np.exp(x)), 1) for t, x in zip(TAUS, q)}      # noqa: E731
    return {"window_start": f"{(555 + tmin) // 60:02d}:{(555 + tmin) % 60:02d}", "window_end": f"{(555 + t1) // 60:02d}:{(555 + t1) % 60:02d}", "sigma_window_pct": round(100 * sig, 3), "high": f(qh), "low": f(ql)}


def eval_row() -> pd.DataFrame | None:
    return pd.read_csv(EVAL) if Path(EVAL).exists() else None


def typical_miss(t: pd.DataFrame | None, tmin: int) -> tuple[float | None, float | None]:
    if t is None or t.empty:
        return None, None
    k = int(np.clip(round(tmin / 15), 1, 23))
    r = t[t.k == k]
    return (None, None) if r.empty else (float(r.high_miss_rs.iloc[0]), float(r.low_miss_rs.iloc[0]))


def load_log() -> list[dict]:
    return [json.loads(x) for x in Path(LOG).read_text().splitlines() if x.strip()] if Path(LOG).exists() else []


def hl_between(df1: pd.DataFrame, a: dt.datetime, b: dt.datetime) -> tuple[float, float, int] | None:
    w = df1[(df1.t >= a) & (df1.t < b)]
    return None if w.empty else (float(w.high.max()), float(w.low.min()), len(w))


def compare(pred: dict | None, act: tuple | None, side: str) -> dict:
    if pred is None or act is None:
        return {}
    q = pred[side]
    a = act[0] if side == "high" else act[1]
    pin = q["0.5"]
    return {"actual": round(a, 1), "predicted": pin, "error_rs": round(a - pin, 1), "inside50": q["0.25"] <= a <= q["0.75"], "inside90": q["0.05"] <= a <= q["0.95"]}


def score_logged(df_all: pd.DataFrame, now_ts) -> int:
    """score EVERY live-logged prediction once its own 60-minute (or shorter, cut at 15:30) window is over, against the Yahoo 1-minute high / low of that window -> results/hourly_table_scored.csv (the learning dataset).
    This is bookkeeping only: the 'this hour' columns of a table still compare with the previous table, nothing else."""
    cols = ["date", "asof", "window", "mode", "pred_high", "act_high", "pred_low", "act_low", "high_in50", "high_in90", "low_in50", "low_in90"]
    old = pd.read_csv(SCORED) if Path(SCORED).exists() else pd.DataFrame(columns=cols)
    done = set(zip(old["date"].astype(str), old["asof"].astype(str))) if "asof" in old.columns else set()
    new = []
    for z in load_log():
        nh = z.get("next_hour")
        if z["mode"] != "live" or not nh or (z["date"], z["asof"]) in done:
            continue
        a = pd.Timestamp(f"{z['date']} {nh['window_start']}", tz=IST); b = pd.Timestamp(f"{z['date']} {nh['window_end']}", tz=IST)
        if now_ts < b + pd.Timedelta(minutes=1):
            continue
        w = df_all[(df_all.t >= a) & (df_all.t < b)]
        if w.empty or w.t.min() > a + pd.Timedelta(minutes=5):      # Yahoo has no bar for a minute without trades: a fetch after the window ended plus coverage of its start is the completeness test
            continue
        act = (float(w.high.max()), float(w.low.min()), len(w))
        ch, cl = compare(nh, act, "high"), compare(nh, act, "low")
        new.append({"date": z["date"], "asof": z["asof"], "window": f"{nh['window_start']}-{nh['window_end']}", "mode": "live", "pred_high": ch["predicted"], "act_high": ch["actual"], "pred_low": cl["predicted"], "act_low": cl["actual"],
                    "high_in50": ch["inside50"], "high_in90": ch["inside90"], "low_in50": cl["inside50"], "low_in90": cl["inside90"]})
    if new:
        pd.concat([old, pd.DataFrame(new)])[cols].to_csv(SCORED, index=False)
    return len(new)


def build(asof: str | None = None, save: bool = True, vs: str | None = None) -> dict | None:
    now = dt.datetime.now(IST)
    df_all, fetched = LH.get_bars(save=True)
    if df_all is None or len(df_all) == 0:
        print("No bars available (Yahoo unreachable or rate-limited, no cache): no row.")
        return None
    sdate = df_all.date.iloc[-1]
    if asof is None:
        if now.weekday() >= 5:
            print(f"{now:%A} {now:%d %b}: weekend, the market is closed (last session {sdate}).")
            return None
        if sdate != now.strftime("%Y-%m-%d"):
            print(f"No Yahoo bars for today ({now:%d %b}): holiday or the feed has not started. Last session in the data: {sdate}.")
            return None
        if not fetched:
            print("WARNING: Yahoo could not be reached; numbers below use CACHED bars and are NOT live.")
    day = df_all[df_all.date == sdate]
    T = dt.datetime.fromisoformat(f"{sdate}T{asof}:00").replace(tzinfo=IST) if asof else now.replace(second=0, microsecond=0)
    d1 = day[day.t < T]
    if d1.empty:
        print(f"No bars before {T:%H:%M} on {sdate}: the session has not started (use --pre-open before 09:15).")
        return None
    tmin = int((T.hour * 60 + T.minute) - OPEN_MIN)
    P = float(d1.close.iloc[-1])
    S = [s for s in load_sessions() if s["date"] != sdate]
    ev, _ = LN.profile(S)
    zh, zl = zpool(S, ev)
    nh = next_hour(P, tmin, ev, zh, zl)
    close = LN.run_live(save=False, asof=asof) if asof else LN.run_live(save=False)
    row = {"date": sdate, "asof": T.strftime("%H:%M"), "mode": "replay" if asof else "live", "price_now": round(P, 1), "close_pin": round(P, 1), "close_50": [round(x, 1) for x in close["close_50"]], "close_90": [round(x, 1) for x in close["close_90"]],
           "close_typical_miss_rs": round(close["typical_miss_rs"], 1), "next_hour": nh, "day_high_so_far": round(float(d1.high.max()), 1), "day_low_so_far": round(float(d1.low.min()), 1)}
    # --- this hour against the PREVIOUS TABLE given to the user: the latest live row logged before this one is compared with what actually happened in ITS window (so far, if that hour is not over).
    #     No replay, no recomputed prediction: if no earlier table exists the cell says so.
    prev, act, complete = None, None, True
    row["this_hour"] = {"from": None, "to": None, "prediction_source": (f"none: no table of {vs} was given today" if vs else "none: no earlier table was given today")}
    for z in reversed(load_log()):
        if z["date"] != sdate or z["mode"] != "live" or not z.get("next_hour") or z["asof"] >= row["asof"] or (vs and z["asof"] != vs):
            continue
        ws = dt.datetime.fromisoformat(f"{sdate}T{z['next_hour']['window_start']}:00").replace(tzinfo=IST)
        we = dt.datetime.fromisoformat(f"{sdate}T{z['next_hour']['window_end']}:00").replace(tzinfo=IST)
        a, b = ws, min(we, T); complete = T >= we
        prev = z["next_hour"]
        row["this_hour"] = {"from": a.strftime("%H:%M"), "to": b.strftime("%H:%M"), "prediction_source": f"the table of {z['asof']}" + ("" if complete else f" (its hour ends {we:%H:%M}: so far only)")}
        act = hl_between(d1, a, b)
        break
    row["this_hour"]["actual_high_low_yahoo"] = None if act is None else [round(act[0], 1), round(act[1], 1)]
    row["this_hour"]["high"] = compare(prev, act, "high"); row["this_hour"]["low"] = compare(prev, act, "low")
    ev_t = eval_row()
    row["typical_miss_next_hour_rs"] = typical_miss(ev_t, tmin)
    if not asof:                                                  # eighth column (context only; forward test H): peers' move since the previous close against BSE's own. Replays carry no peers.
        try:
            import peers_live as PL
            row["peers"] = PL.snapshot(T, P, LN.prev_close_before(sdate))
        except Exception as e:                                    # noqa: BLE001  (shown in the cell, never blocks the table)
            row["peers"] = {"error": f"{type(e).__name__}: {e}"}
    if save and not asof:
        try:                                                      # paper ledger (src/paper_hourly.py): settle finished hours, place this row's paper orders
            import paper_hourly as PH
            row["paper"] = {"settled": PH.settle(df_all[df_all.date >= (T - dt.timedelta(days=6)).strftime('%Y-%m-%d')], pd.Timestamp(now), PH.ORDERS, PH.LEDGER), "placed": PH.place(row, PH.ORDERS)}
        except Exception as e:                                    # noqa: BLE001  (never hide a failure: it is printed under the table)
            row["paper"] = {"error": f"{type(e).__name__}: {e}"}
        Path("results").mkdir(exist_ok=True)
        with open(LOG, "a") as f:
            f.write(json.dumps({**row, "logged_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}) + "\n")
    if save:
        row["scored_now"] = score_logged(df_all, pd.Timestamp(now))
        if not asof:
            refresh_readings()
    return row


def fmt_row(r: dict) -> str:
    nh = r["next_hour"]
    H, L = (f"{nh['high']['0.5']:,.0f} (half the time {nh['high']['0.25']:,.0f}-{nh['high']['0.75']:,.0f}; 9 in 10 {nh['high']['0.05']:,.0f}-{nh['high']['0.95']:,.0f})", f"{nh['low']['0.5']:,.0f} (half the time {nh['low']['0.25']:,.0f}-{nh['low']['0.75']:,.0f}; 9 in 10 {nh['low']['0.05']:,.0f}-{nh['low']['0.95']:,.0f})") if nh else ("market closes", "market closes")
    th = r["this_hour"]

    def cell(side):
        c = th[side]
        if not c:
            return "n/a: no earlier table to compare with"
        s = "high" if side == "high" else "low"
        return (f"{th['from']}-{th['to']}: actual {c['actual']:,.1f} vs predicted {c['predicted']:,.1f}: off by {c['error_rs']:+,.1f}; inside half-the-time range: {'yes' if c['inside50'] else 'no'}; inside 9-in-10: {'yes' if c['inside90'] else 'no'} "
                f"[{th['prediction_source']}]")
    tm = r["typical_miss_next_hour_rs"]
    head = "| time | precise close | close range at the end of the day | precise high of the next hour | precise low of the next hour | this hour's high vs previous prediction | this hour's low vs previous prediction |\n|---|---|---|---|---|---|---|"
    body = f"| {r['asof']} | {r['close_pin']:,.1f} (typical miss {r['close_typical_miss_rs']:,.0f}) | half the time {r['close_50'][0]:,.0f}-{r['close_50'][1]:,.0f}; 9 in 10 {r['close_90'][0]:,.0f}-{r['close_90'][1]:,.0f} | {H} | {L} | {cell('high')} | {cell('low')} |"
    if "peers" in r:                                              # eighth column from 22 Oct 2026 (forward test H); earlier rows and replays keep the seven-column format exactly as they were printed
        import peers_live as PL
        head = head.replace(" prediction |\n|---|---|---|---|---|---|---|", " prediction | peers' move today vs BSE's |\n|---|---|---|---|---|---|---|---|")
        body += f" {PL.words(r['peers'])} |"
    foot = [f"Window of the next-hour columns: {nh['window_start']}-{nh['window_end']} IST." if nh else "", f"Typical miss of the next-hour pin-points at this time (leave-one-session-out, past sessions): high Rs {tm[0]:,.0f}, low Rs {tm[1]:,.0f}." if tm[0] is not None else "Typical miss of the next-hour pin-points: run --eval.",
            f"Day so far (Yahoo): high {r['day_high_so_far']:,.1f}, low {r['day_low_so_far']:,.1f}; this hour's actual high/low are Yahoo 1-minute figures (NSE's official ones can differ by a few rupees)."]
    pp = r.get("paper")
    if pp:
        foot.append(f"Paper ledger FAILED this time ({pp['error']})." if "error" in pp else f"Paper ledger (src/paper_hourly.py): {pp['placed']} new paper orders placed for this window, {pp['settled']} older orders settled. Backtest verdict: no rule beats doing nothing.")
    return head + "\n" + body + "\n" + "\n".join(x for x in foot if x)


def peer_forward_update() -> None:
    """Forward test H (peer column): rebuild results/peer_forward/dataset.csv and print the LOCKED counts line (src/peer_forward.py); a problem is printed, never hidden, and never blocks the scoring."""
    try:
        import peer_forward as PF
        PF.update()
    except Exception as e:                                                 # noqa: BLE001
        print(f"(forward test H not updated: {type(e).__name__}: {e})")


def refresh_readings() -> None:
    """Rewrite results/readings/readings.csv and results/readings/by_day/<date>.csv from the logs (src/readings_csv.py); a CSV problem is printed, never hidden, and never blocks the reading."""
    try:
        import readings_csv as RC
        RC.rebuild()
    except Exception as e:                                                 # noqa: BLE001
        print(f"(readings CSV not refreshed: {type(e).__name__}: {e})")


# ------------------------------------------------------------------ before the open
def pre_open() -> None:
    now = dt.datetime.now(IST)
    pc = LN.prev_close_before(now.strftime("%Y-%m-%d"))
    ent = None
    for p in sorted(Path("results/scoreboard/entries").glob("*.json")):
        e = json.loads(p.read_text())
        if e["target_session"] == now.strftime("%Y-%m-%d"):
            ent = e
    lines = [f"Before the open ({now:%a %d %b %H:%M} IST). Previous official close: Rs {pc:,.1f}."]
    if ent:
        q = ent["open"]["price"]
        lines.append(f"Open range (issued {ent['made_at_ist'][11:16]} IST, committed before the open): pin-point Rs {q['q0.5']:,.1f}; half the time Rs {q['q0.25']:,.0f}-{q['q0.75']:,.0f}; 9 in 10 Rs {q['q0.05']:,.0f}-{q['q0.95']:,.0f}.  The pin-point is the previous close: nothing tested beats it.")
    else:
        lines.append("No scoreboard entry for today yet: run python3 src/scoreboard.py issue first (open range comes from it).")
    try:
        import preopen as PO
        s = PO.fetch("BSE")
        p = s["pre"]
        t = p["lastUpdateTime"]
        st = PO.status(s, now)
        PO.save_snapshot(s, "BSE", st, now)                    # kept (never when STALE) so the 09:00 reading is stored in results/preopen and in the readings CSV
        if st == "STALE":
            lines.append(f"NSE pre-open: no order data for today yet (the page still shows {t}). It opens 09:00; the price is fixed when order entry closes at a random moment between 09:08 and 09:10 (since 7 Sep 2026); no page at all on a holiday.")
        else:
            lbl = {"FINAL": "FINAL = the official opening price", "NO_PRICE": "NOT DISCOVERED: the open will be the first trade"}.get(st, "INDICATIVE: can still change until NSE closes order entry, between 09:08 and 09:10")
            px = float(p["IEP"])                                   # the equilibrium price, also when FINAL: the finalPrice field held the previous close on 26 Oct (official open = IEP)
            lines.append(f"NSE pre-open price at {t[-8:]}: Rs {px:,.1f} ({lbl}); buy orders {int(p['totalBuyQuantity']):,} vs sell orders {int(p['totalSellQuantity']):,} (shares).")
    except SystemExit as e:                        # noqa: BLE001
        lines.append(f"NSE pre-open could not be read ({e}).")
    except Exception as e:                         # noqa: BLE001
        lines.append(f"NSE pre-open could not be read ({e}).")
    print("\n".join(lines))
    refresh_readings()


def report() -> None:
    if not Path(SCORED).exists():
        print("No scored predictions yet."); return
    d = pd.read_csv(SCORED)
    for mode, g in d.groupby("mode"):
        n = len(g)
        print(f"{mode}: {n} scored predictions (overlapping hours count separately);  typical miss: high Rs {(g.pred_high - g.act_high).abs().mean():.1f}, low Rs {(g.pred_low - g.act_low).abs().mean():.1f};  inside half-the-time range: high {g.high_in50.mean():.0%}, low {g.low_in50.mean():.0%};  inside 9-in-10: high {g.high_in90.mean():.0%}, low {g.low_in90.mean():.0%}  (n is small: a guide, not proof)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--asof", default=None); ap.add_argument("--vs", default=None, help="compare this hour with the table given at HH:MM (default: the previous table)"); ap.add_argument("--score", action="store_true"); ap.add_argument("--eval", action="store_true"); ap.add_argument("--report", action="store_true"); ap.add_argument("--pre-open", action="store_true"); ap.add_argument("--nosave", action="store_true")
    a = ap.parse_args()
    if a.eval:
        S = load_sessions(); t = loo_eval(S); Path("results").mkdir(exist_ok=True); t.to_csv(EVAL, index=False)
        print(f"{len(S)} sessions; leave-one-session-out; next-hour high/low pin-point = median; typical miss in rupees (price stays = P):")
        print(t[["time", "n_sessions", "high_miss_rs", "high_stays_miss_rs", "low_miss_rs", "low_stays_miss_rs", "high_cov50", "high_cov90", "low_cov50", "low_cov90"]].to_string(index=False))
    elif a.score:
        df_all, _ = LH.get_bars(save=True); print(f"scored {score_logged(df_all, pd.Timestamp.now(tz=IST))} new live predictions"); report(); peer_forward_update(); refresh_readings()
    elif a.report:
        report()
    elif a.pre_open:
        pre_open()
    else:
        r = build(a.asof, save=not a.nosave, vs=a.vs)
        if r:
            print(fmt_row(r))

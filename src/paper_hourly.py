"""Hour-by-hour paper trade built on the next-hour high/low pin-points (rules fixed in docs/PAPER_TRADE_HOURLY.md BEFORE any backtest).

  python3 src/paper_hourly.py --backtest     # leave-one-session-out backtest of rules R-A..R-E on the 39 post-closing-auction sessions + random-walk placebo
  python3 src/paper_hourly.py --report       # the live paper ledger so far (results/paper_hourly_ledger.csv)
Live paper ledger: every live row of src/hourly_table.py (window of a full 60 minutes) places the five paper orders from that row's pin-points (results/paper_hourly_orders.jsonl, append only); every later row settles the
orders whose hour is over, on the 1-minute bars (strict-through fills, stop first if stop and target share a minute, 0.10% round trip) -> results/paper_hourly_ledger.csv.
Paper only: no orders are ever sent anywhere.  Backtest verdict (see docs/PAPER_TRADE_HOURLY.md): none of the rules beats doing nothing.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hourly_table as HT      # noqa: E402
import live_nowcast as LN      # noqa: E402

COST = 0.0010                           # 0.10% round trip on every filled trade
CKS = (3, 7, 11, 15, 19)               # 10:00, 11:00, 12:00, 13:00, 14:00 (completed 15-minute bars)
RULES = ["R-A", "R-B", "R-C", "R-D", "R-E"]
NAMES = {"R-A": "buy the dip (limit at predicted low)", "R-B": "sell the pop (limit short at predicted high)", "R-C": "long, target = predicted high, stop = predicted low",
         "R-D": "short, target = predicted low, stop = predicted high", "R-E": "control: buy now, sell at hour end"}


def run_rules(P: float, hs: np.ndarray, ls: np.ndarray, c_end: float, Hs: float, Ls: float) -> dict:
    """one window of 4 bars (highs hs, lows ls, close of the last bar c_end) -> net return per rule (None = no trade)."""
    out = {}
    out["R-A"] = (c_end / Ls - 1 - COST) if (ls < Ls).any() else None
    out["R-B"] = ((Hs - c_end) / Hs - COST) if (hs > Hs).any() else None
    for rule, long in (("R-C", True), ("R-D", False)):
        stop, tgt = (Ls, Hs) if long else (Hs, Ls)
        res = None
        for h, l in zip(hs, ls):
            hit_stop = (l < stop) if long else (h > stop)
            hit_tgt = (h > tgt) if long else (l < tgt)
            if hit_stop:
                res = (stop / P - 1) if long else ((P - stop) / P); break         # stop first if both inside one bar
            if hit_tgt:
                res = (tgt / P - 1) if long else ((P - tgt) / P); break
        if res is None:
            res = (c_end / P - 1) if long else ((P - c_end) / P)
        out[rule] = res - COST
    out["R-E"] = c_end / P - 1 - COST
    return out


def backtest() -> pd.DataFrame:
    S = HT.load_sessions()
    rows = []
    for i, s in enumerate(S):
        others = [x for j, x in enumerate(S) if j != i]
        ev, _ = LN.profile(others)
        zh, zl = HT.zpool(others, ev)
        qh, ql = np.quantile(zh, 0.5), np.quantile(zl, 0.5)
        for k in CKS:
            end = k + 3
            if np.isnan(s["h"][k:end + 1]).any() or np.isnan(s["cf"][k - 1]):
                continue
            P = s["cf"][k - 1]
            sig = float(np.sqrt(ev[k:end + 1].sum()))
            Hs, Ls = P * np.exp(qh * sig), P * np.exp(ql * sig)
            r = run_rules(P, s["h"][k:end + 1], s["l"][k:end + 1], s["cf"][end], Hs, Ls)
            for rule, v in r.items():
                rows.append({"date": s["date"], "k": k, "rule": rule, "net": v})
    return pd.DataFrame(rows)


def placebo(S: list[dict], reps: int = 400, seed: int = 11) -> pd.DataFrame:
    """random-walk sessions with the real time-of-day variance profile; same pin-point method, same rules: what a no-edge world pays."""
    rng = np.random.default_rng(seed)
    ev, _ = LN.profile(S)
    zh, zl = HT.zpool(S, ev)
    qh, ql = np.quantile(zh, 0.5), np.quantile(zl, 0.5)
    rows = []
    for k in CKS:
        sig = float(np.sqrt(ev[k:k + 4].sum()))
        for rep in range(reps):
            sd = np.sqrt(ev[k:k + 4] / 15)[:, None]
            steps = rng.normal(0, 1, (4, 15)) * sd                                       # 1-minute increments in 4 bars
            x1 = np.cumsum(steps.reshape(-1))                                             # log level at each minute close (start = 0)
            x0 = np.r_[0.0, x1[:-1]]
            var = np.repeat(sd[:, 0] ** 2, 15)
            ub, vb = rng.uniform(size=60), rng.uniform(size=60)
            mx = (x0 + x1 + np.sqrt((x1 - x0) ** 2 - 2 * var * np.log(ub))) / 2           # exact maximum / minimum of a Brownian bridge between the two minute closes
            mn = (x0 + x1 - np.sqrt((x1 - x0) ** 2 - 2 * var * np.log(vb))) / 2
            hs = np.exp(mx.reshape(4, 15).max(axis=1)); ls = np.exp(mn.reshape(4, 15).min(axis=1)); lvl = np.exp(x1.reshape(4, 15))
            r = run_rules(1.0, hs, ls, lvl[-1, -1], np.exp(qh * sig), np.exp(ql * sig))
            for rule, v in r.items():
                rows.append({"k": k, "rule": rule, "net": v, "rep": rep})
    return pd.DataFrame(rows)


def summarise(bt: pd.DataFrame, pl: pd.DataFrame) -> pd.DataFrame:
    out = []
    dates = sorted(bt.date.unique()); half = set(dates[: len(dates) // 2])
    for rule in RULES:
        g = bt[(bt.rule == rule) & bt.net.notna()]
        n_all = (bt.rule == rule).sum()
        per = g.groupby("date").net.mean()                   # session-clustered
        t = per.mean() / (per.std(ddof=1) / np.sqrt(len(per))) if len(per) > 2 and per.std(ddof=1) > 0 else np.nan
        h1, h2 = g[g.date.isin(half)].net, g[~g.date.isin(half)].net
        p = pl[(pl.rule == rule) & pl.net.notna()]
        pm, pse = p.net.mean(), p.net.std(ddof=1) / np.sqrt(len(p))
        z_vs_placebo = (g.net.mean() - pm) / np.sqrt(per.std(ddof=1) ** 2 / len(per) + pse ** 2) if len(per) > 2 else np.nan
        out.append({"rule": rule, "what": NAMES[rule], "windows": int(n_all), "trades": len(g), "fill_rate": round(len(g) / n_all, 3), "mean_net_pct": round(100 * g.net.mean(), 3), "median_net_pct": round(100 * g.net.median(), 3),
                    "win_rate": round(float((g.net > 0).mean()), 3), "session_avg_net_pct": round(100 * float(per.mean()), 3), "t_session_avg": round(float(t), 2), "first_half_mean_pct": round(100 * h1.mean(), 3), "second_half_mean_pct": round(100 * h2.mean(), 3),
                    "placebo_mean_pct": round(100 * pm, 3), "placebo_fill_rate": round(len(p) / (pl.rule == rule).sum(), 3), "z_vs_placebo": round(float(z_vs_placebo), 2),
                    "better_than_nothing": bool(g.net.mean() > 0 and t > 2 and h1.mean() > 0 and h2.mean() > 0 and z_vs_placebo > 2)})
    return pd.DataFrame(out)


ORDERS = "results/paper_hourly_orders.jsonl"
LEDGER = "results/paper_hourly_ledger.csv"


def place(row: dict, orders: str = ORDERS) -> int:
    """append the five paper orders for a LIVE row (full 60-minute window only); returns how many were new."""
    nh = row.get("next_hour")
    if row.get("mode") != "live" or not nh:
        return 0
    t0, t1 = (int(nh["window_start"][:2]) * 60 + int(nh["window_start"][3:])), (int(nh["window_end"][:2]) * 60 + int(nh["window_end"][3:]))
    if t1 - t0 < 60:
        return 0
    have = set()
    if Path(orders).exists():
        have = {json.loads(x)["id"] for x in Path(orders).read_text().splitlines() if x.strip()}
    new = 0
    with open(orders, "a") as f:
        for rule in RULES:
            oid = f"{row['date']}_{nh['window_start']}_{rule}"
            if oid in have:
                continue
            f.write(json.dumps({"id": oid, "date": row["date"], "placed_at": row["asof"], "window_start": nh["window_start"], "window_end": nh["window_end"], "rule": rule, "P": row["price_now"],
                                "H_star": nh["high"]["0.5"], "L_star": nh["low"]["0.5"]}) + "\n")
            new += 1
    return new


def settle(bars_1m: pd.DataFrame, now, orders: str = ORDERS, ledger: str = LEDGER) -> int:
    """settle every order whose window is over (all minutes of the window are in bars_1m) on the 1-minute bars; returns how many were settled."""
    if not Path(orders).exists():
        return 0
    done = set(pd.read_csv(ledger).id) if Path(ledger).exists() else set()
    out = []
    for line in Path(orders).read_text().splitlines():
        if not line.strip():
            continue
        o = json.loads(line)
        if o["id"] in done:
            continue
        a = pd.Timestamp(f"{o['date']} {o['window_start']}", tz=LN.IST); b = pd.Timestamp(f"{o['date']} {o['window_end']}", tz=LN.IST)
        if now < b + pd.Timedelta(minutes=1):
            continue
        w = bars_1m[(bars_1m.t >= a) & (bars_1m.t < b)].sort_values("t")
        if w.empty or w.t.min() > a + pd.Timedelta(minutes=5):                                          # no data for the start of the hour: do not settle on a guess
            continue
        wt = w[w.volume > 0]                                                                            # zero-volume rows are quote snapshots, not trades: exit on the last traded minute
        if wt.empty:
            continue
        w = wt
        P, Hs, Ls, end = o["P"], o["H_star"], o["L_star"], float(w.close.iloc[-1])
        hs, ls = w.high.values, w.low.values
        r = None; how = ""
        if o["rule"] == "R-A":
            r = (end / Ls - 1) if (ls < Ls).any() else None; how = "filled" if r is not None else "no fill"
        elif o["rule"] == "R-B":
            r = ((Hs - end) / Hs) if (hs > Hs).any() else None; how = "filled" if r is not None else "no fill"
        elif o["rule"] in ("R-C", "R-D"):
            long = o["rule"] == "R-C"; stop, tgt = (Ls, Hs) if long else (Hs, Ls); how = "hour end"; r = (end / P - 1) if long else ((P - end) / P)
            for h, l in zip(hs, ls):
                if (l < stop) if long else (h > stop):
                    r = (stop / P - 1) if long else ((P - stop) / P); how = "stop"; break
                if (h > tgt) if long else (l < tgt):
                    r = (tgt / P - 1) if long else ((P - tgt) / P); how = "target"; break
        else:
            r = end / P - 1; how = "hour end"
        out.append({"id": o["id"], "date": o["date"], "window": f"{o['window_start']}-{o['window_end']}", "rule": o["rule"], "P": P, "H_star": Hs, "L_star": Ls, "exit_close": round(end, 1), "how": how,
                    "net_pct": None if r is None else round(100 * (r - COST), 3), "source": "Yahoo 1-minute bars (unofficial)"})
    if out:
        old = pd.read_csv(ledger) if Path(ledger).exists() else pd.DataFrame()
        pd.concat([old, pd.DataFrame(out)]).to_csv(ledger, index=False)
    return len(out)


def report() -> None:
    if not Path(LEDGER).exists():
        print("No settled paper orders yet."); return
    d = pd.read_csv(LEDGER)
    for rule in RULES:
        g = d[(d.rule == rule) & d.net_pct.notna()]
        n_w = int((d.rule == rule).sum())
        if g.empty:
            print(f"{rule} {NAMES[rule]}: {n_w} windows, no fills yet"); continue
        print(f"{rule} {NAMES[rule]}: {n_w} windows, {len(g)} trades, mean net {g.net_pct.mean():+.3f}% per trade, win rate {100*(g.net_pct>0).mean():.0f}%, total {g.net_pct.sum():+.2f}% (0.10% cost included; n is small: a guide, not proof)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--backtest", action="store_true"); ap.add_argument("--report", action="store_true"); ap.add_argument("--settle", action="store_true", help="settle every finished order on the cached 1-minute bars")
    a = ap.parse_args()
    if a.settle:
        import hourly_table as _HT
        df_all, _ = _HT.LH.get_bars(save=True)
        print(f"settled {settle(df_all, pd.Timestamp.now(tz=LN.IST))} orders"); report(); raise SystemExit
    if a.report:
        report(); raise SystemExit
    if a.backtest:
        S = HT.load_sessions()
        bt = backtest(); pl = placebo(S)
        Path("results").mkdir(exist_ok=True)
        bt.to_csv("results/paper_hourly_trades.csv", index=False)
        s = summarise(bt, pl); s.to_csv("results/paper_hourly_backtest.csv", index=False)
        pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
        print(f"{bt.date.nunique()} sessions, checkpoints 10:00-14:00, costs {100*COST:.2f}% round trip, strict-through fills; placebo = {pl.rep.nunique()} random-walk windows per checkpoint")
        print(s.drop(columns=["what"]).to_string(index=False))
        print(s[["rule", "what"]].to_string(index=False))

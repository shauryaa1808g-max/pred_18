"""Challenger ("v2 clone") against the champion: the pre-registered FORWARD comparison of research/hl/I_challenger.md (read its Section 0 first).

The champion (everything the user sees) is unchanged.  This module adds, silently:
  C1  next-hour high / low with the day's volatility so far (w fitted once on history, frozen in results/challenger/w_frozen.json; w = 0 means identical to the champion);
  C2  the pre-open order-book numbers of every session, RECORDED only (a forward lead test, never applied).

  python3 src/challenger.py --fit          # leave-one-session-out choice of w on the history (writes results/challenger/fit_w.csv; --write also freezes w_frozen.json)
  python3 src/challenger.py --update       # score the logged pairs, record C2, print the ONE locked line (and a pre-registered look when its session count is reached)
  python3 src/challenger.py --selftest     # synthetic-data tests of the analysis code
  python3 src/challenger.py --status       # the locked line only
Locked reporting: before the 10-session look only counts are printed; p-values appear only at 40 / 60 sessions; the C2 slope only at 60 / 120 sessions.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hourly_table as HT      # noqa: E402  (the champion's table code: profile, pool, next hour)
import live_nowcast as LN      # noqa: E402

NB = LN.NB
TAUS = HT.TAUS
DIR = Path("results/challenger")
LOGF, BOOK, DATA, WFILE, FITF = DIR / "hourly_log.jsonl", DIR / "book_features.csv", DIR / "compare_dataset.csv", DIR / "w_frozen.json", DIR / "fit_w.csv"
GRID = (0.0, 0.25, 0.5, 0.75, 1.0)
CLIP = (0.5, 2.0)
SEED, NPERM = 20261029, 20000
LOOKS = (10, 40, 60)
MIN_READINGS = 4
FIRST_SESSION = "2026-10-29"
SPECIAL = {"2026-11-08"}                  # Muhurat evening session: excluded
HB_LOOKS = (60, 120)


# ------------------------------------------------------------------ C1: the prediction
def ratio_sofar(r2_sum: float, ev: np.ndarray, m: int) -> float:
    """realised variance of the m completed 15-minute bars over the profile's expected variance of the same bars (1 when no bar is complete)."""
    if m <= 0:
        return 1.0
    cum = float(ev[:m].sum())
    return r2_sum / cum if cum > 0 else 1.0


def scale2(ratio: float, w: float) -> float:
    return float(np.clip((1.0 - w) + w * ratio, CLIP[0], CLIP[1]))


def pool_z(S: list[dict], ev: np.ndarray, w: float, dayscale: dict | None = None) -> tuple[np.ndarray, np.ndarray]:
    """pooled excursions standardised by the SAME scaled sigma the prediction uses (Sections 1.1 and 2); w = 0 and no dayscale reproduce hourly_table.zpool exactly.
    dayscale = {session date: C3's scale2_d}."""
    ex = HT.excursions(S, ev)
    byd = {s["date"]: s["r"] for s in S}
    sc = np.array([scale2(ratio_sofar(float(np.nansum(byd[d][:int(k)] ** 2)), ev, int(k)), w) * (1.0 if dayscale is None else dayscale[d]) for d, k in zip(ex.date, ex.k)])
    sig = ex.sig.values * np.sqrt(sc)
    return (ex.Xh.values / sig), (ex.Xl.values / sig)


def sigma_I_map(day: str) -> dict:
    """C3's ingredient: the daily model's walk-forward S6 sigma of the open-to-close return for every session before `day`, and (key `day`) its forecast for `day` from the sessions before it.  Cached per day."""
    f = DIR / f"sigmaI_{day}.json"
    if f.exists():
        return json.loads(f.read_text())
    import hl_model as HM
    d = HM.load_ohlc(pd.Timestamp(day)); t = HM.targets(d); I, gk = t["I"].values, t["gk"].values
    path = HM.wf_sigmas(I, gk, ("S6",))["S6"]
    m = {str(x.date()): float(s) for x, s in zip(d.index, path) if np.isfinite(s)}
    m[day] = float(HM.s6_next(I, gk))
    DIR.mkdir(parents=True, exist_ok=True); f.write_text(json.dumps(m))
    return m


def day_scales(sI: dict, dates: list[str], w3: float) -> dict:
    """scale2_d for each date: ratio_d = sI^2 over the mean of sI^2 across `dates` (the sessions of the pool)."""
    den = float(np.mean([sI[d] ** 2 for d in dates]))
    return {d: scale2(sI[d] ** 2 / den, w3) for d in dates}


def next_hour_v2(P: float, tmin: int, ev: np.ndarray, zh: np.ndarray, zl: np.ndarray, sc2: float) -> dict | None:
    """as hourly_table.next_hour, with the window sigma times sqrt(scale2)."""
    t1 = min(tmin + HT.WIN, HT.CLOSE_MIN - HT.OPEN_MIN)
    if tmin >= HT.CLOSE_MIN - HT.OPEN_MIN or t1 <= tmin:
        return None
    sig = HT.sigma_window(ev, tmin, t1) * math.sqrt(sc2)
    qh, ql = np.quantile(zh, TAUS) * sig, np.quantile(zl, TAUS) * sig
    f = lambda q: {str(t): round(float(P * np.exp(x)), 1) for t, x in zip(TAUS, q)}      # noqa: E731
    return {"window_start": f"{(555 + tmin) // 60:02d}:{(555 + tmin) % 60:02d}", "window_end": f"{(555 + t1) // 60:02d}:{(555 + t1) % 60:02d}", "sigma_window_pct": round(100 * sig, 3), "high": f(qh), "low": f(ql)}


def live_r2(day1: pd.DataFrame, T, m: int) -> float:
    """sum of squared 15-minute log returns of the m slots completed before T from today's 1-minute bars (the first return starts at the first bar's open, as in hourly_table.load_sessions)."""
    d = day1[day1.t < T]
    if m <= 0 or d.empty:
        return 0.0
    slot = ((d.t.dt.hour * 60 + d.t.dt.minute) - 555) // 15
    g = d.assign(slot=slot).groupby("slot").close.last()
    c = pd.Series(np.nan, index=range(NB)); c.loc[g.index] = g.values
    c = c.ffill().fillna(float(d.open.iloc[0]))
    r = np.diff(np.log(np.r_[float(d.open.iloc[0]), c.values[:m]]))
    return float(np.sum(r ** 2))


def frozen_w() -> tuple[float, float]:
    """(w for C1, w3 for C3), frozen in results/challenger/w_frozen.json."""
    if not WFILE.exists():
        raise RuntimeError("w is not frozen yet (results/challenger/w_frozen.json missing)")
    j = json.loads(WFILE.read_text())
    return float(j["w"]), float(j["w3"])


def record(row: dict, S: list[dict], ev: np.ndarray, day1: pd.DataFrame, T, tmin: int) -> dict:
    """called by hourly_table.build for every LIVE row: compute the challenger's next hour beside the champion's and append both to results/challenger/hourly_log.jsonl."""
    w, w3 = frozen_w()
    if w == 0 and w3 == 0:                                                       # identical to the champion: nothing to log beside it
        return {"identical": True, "w": 0.0, "w3": 0.0}
    m = max(0, tmin // 15)
    ratio = ratio_sofar(live_r2(day1, T, m), ev, m)
    sc1 = scale2(ratio, w)
    ds, sc3 = None, 1.0
    if w3 > 0:                                                                   # C3 (only when its weight is not zero: with w3 = 0 the daily model is not even touched)
        sI = sigma_I_map(row["date"])
        den = float(np.mean([sI[s["date"]] ** 2 for s in S]))
        ds = {s["date"]: scale2(sI[s["date"]] ** 2 / den, w3) for s in S}
        sc3 = scale2(sI[row["date"]] ** 2 / den, w3)
    zh, zl = pool_z(S, ev, w, ds)
    nh2 = next_hour_v2(row["price_now"], tmin, ev, zh, zl, sc1 * sc3)
    DIR.mkdir(parents=True, exist_ok=True)
    rec = {"date": row["date"], "asof": row["asof"], "price_now": row["price_now"], "w": w, "w3": w3, "completed_slots": m, "ratio": round(ratio, 4), "scale2": round(sc1 * sc3, 4), "scale2_c1": round(sc1, 4), "scale2_c3": round(sc3, 4),
           "champion": row["next_hour"], "challenger": nh2, "logged_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    with open(LOGF, "a") as f:
        f.write(json.dumps(rec) + "\n")
    return {"w": w, "w3": w3, "scale2": round(sc1 * sc3, 4)}


# ------------------------------------------------------------------ choosing w (history only; Section 0.3)
def pinball(pred: np.ndarray, act: float) -> float:
    e = act - pred
    return float(np.mean(np.maximum(TAUS * e, (TAUS - 1.0) * e)))


def fit_w(S: list[dict], grid=GRID, mode: str = "c1", sI: dict | None = None) -> pd.DataFrame:
    """leave-one-session-out losses for each weight in the grid.  mode 'c1': w = the weight on today's volatility so far; mode 'c3': w = the weight w3 on the daily model's sigma (needs sI = sigma_I_map)."""
    rows = []
    for i, s in enumerate(S):
        others = [x for j, x in enumerate(S) if j != i]
        ev, _ = LN.profile(others)
        ex = HT.excursions([s], ev)
        for w in grid:
            w1, w3 = (w, 0.0) if mode == "c1" else (0.0, w)
            ds = None
            if mode == "c3":                                                    # denominator = the pool's sessions only (the held-out session's own sigma is not in it), as in live use
                den = float(np.mean([sI[x["date"]] ** 2 for x in others]))
                ds = {x["date"]: scale2(sI[x["date"]] ** 2 / den, w3) for x in others} | {s["date"]: scale2(sI[s["date"]] ** 2 / den, w3)}
            zh, zl = pool_z(others, ev, w1, ds)
            qh, ql = np.quantile(zh, TAUS), np.quantile(zl, TAUS)
            for _, r in ex.iterrows():
                k = int(r.k)
                if k < 2 or k > 22:
                    continue
                sc = scale2(ratio_sofar(float(np.nansum(s["r"][:k] ** 2)), ev, k), w1) * (1.0 if ds is None else ds[s["date"]])
                sig = r.sig * math.sqrt(sc)
                P = r.P
                ha, la = P * math.exp(r.Xh), P * math.exp(r.Xl)
                ph, pl = P * np.exp(qh * sig), P * np.exp(ql * sig)
                rows.append((s["date"], w, k, pinball(ph, ha), pinball(pl, la), abs(ph[2] - ha), abs(pl[2] - la)))
    return pd.DataFrame(rows, columns=["date", "w", "k", "pin_high", "pin_low", "ae_high", "ae_low"])


def choose_w(F: pd.DataFrame) -> tuple[float, pd.DataFrame]:
    g = F.groupby("w").agg(pinball=("pin_high", "mean"), pin_low=("pin_low", "mean"), ae_high=("ae_high", "mean"), ae_low=("ae_low", "mean"), n=("k", "size"))
    g["pinball"] = (g.pinball + g.pin_low) / 2
    base = float(g.loc[0.0, "pinball"])
    g["gain_vs_w0_pct"] = 100 * (base - g.pinball) / base
    ok = g[(g.index > 0) & (g.gain_vs_w0_pct >= 1.0)]
    w = float(ok.pinball.idxmin()) if len(ok) else 0.0
    return w, g.drop(columns="pin_low").round(4)


# ------------------------------------------------------------------ shared statistics
def perm_p(d: np.ndarray, seed: int = SEED, nperm: int = NPERM) -> float:
    """one-sided (mean > 0) sign-flip permutation p-value."""
    d = np.asarray(d, float)
    if len(d) < 2:
        return float("nan")
    rng = np.random.default_rng(seed)
    obs = d.mean()
    flips = rng.choice([-1.0, 1.0], size=(nperm, len(d)))
    return float((1 + np.sum((flips * d).mean(axis=1) >= obs - 1e-12)) / (1 + nperm))


def holm(ps: dict[str, float]) -> dict[str, float]:
    items = sorted(ps.items(), key=lambda kv: kv[1]); m = len(items); out, run = {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p)); out[k] = run
    return out


def slope_perm_p(x: np.ndarray, y: np.ndarray, seed: int = SEED, nperm: int = NPERM) -> tuple[float, float]:
    """OLS slope of y on x and its one-sided (slope > 0) permutation p-value."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    xc = x - x.mean()
    b = float((xc * (y - y.mean())).sum() / (xc ** 2).sum())
    rng = np.random.default_rng(seed)
    yy = y - y.mean()
    cnt = 0
    for _ in range(nperm):
        cnt += (xc * rng.permutation(yy)).sum() / (xc ** 2).sum() >= b - 1e-12
    return b, float((1 + cnt) / (1 + nperm))


# ------------------------------------------------------------------ forward dataset and C1 comparison
def build_dataset() -> pd.DataFrame:
    """one row per scored live reading from FIRST_SESSION on: both pin-points beside the actual window high / low (the champion's scorer file)."""
    if not LOGF.exists() or not Path(HT.SCORED).exists():
        return pd.DataFrame()
    sc = pd.read_csv(HT.SCORED); sc = sc[sc["mode"] == "live"]
    key = {(str(r.date), str(r.asof)): r for r in sc.itertuples()}
    out = []
    for z in (json.loads(x) for x in LOGF.read_text().splitlines() if x.strip()):
        r = key.get((z["date"], z["asof"]))
        if r is None or z["date"] < FIRST_SESSION or not z.get("challenger") or not z.get("champion"):
            continue
        out.append({"date": z["date"], "asof": z["asof"], "w": z["w"], "w3": z.get("w3", 0.0), "scale2": z["scale2"], "act_high": r.act_high, "act_low": r.act_low,
                    "champ_high": z["champion"]["high"]["0.5"], "champ_low": z["champion"]["low"]["0.5"], "chall_high": z["challenger"]["high"]["0.5"], "chall_low": z["challenger"]["low"]["0.5"]})
    d = pd.DataFrame(out)
    if not d.empty:
        d = d.drop_duplicates(["date", "asof"], keep="last")
        DIR.mkdir(parents=True, exist_ok=True); d.to_csv(DATA, index=False)
    return d


def eligible_sessions(d: pd.DataFrame) -> pd.DataFrame:
    """session-level means of the absolute errors of the median pin-points; eligible = 4+ scored readings, a normal session."""
    if d.empty:
        return pd.DataFrame()
    d = d.assign(ec_h=(d.champ_high - d.act_high).abs(), ex_h=(d.chall_high - d.act_high).abs(), ec_l=(d.champ_low - d.act_low).abs(), ex_l=(d.chall_low - d.act_low).abs())
    g = d.groupby("date").agg(n=("asof", "size"), ec_h=("ec_h", "mean"), ex_h=("ex_h", "mean"), ec_l=("ec_l", "mean"), ex_l=("ex_l", "mean")).reset_index()
    return g[(g.n >= MIN_READINGS) & (~g.date.isin(SPECIAL))].sort_values("date").reset_index(drop=True)


def compare(E: pd.DataFrame, nlook: int) -> dict:
    """the pre-registered comparison on the FIRST nlook eligible sessions."""
    E = E.iloc[:nlook]
    res = {"n_sessions": len(E)}
    ps, pr = {}, {}
    for side, c, x in (("high", "ec_h", "ex_h"), ("low", "ec_l", "ex_l")):
        dd = (E[c] - E[x]).values
        mc, mx = float(E[c].mean()), float(E[x].mean())
        h = len(E) // 2
        res[side] = {"mean_ae_champion": round(mc, 3), "mean_ae_challenger": round(mx, 3), "gain_pct": round(100 * (mc - mx) / mc, 2) if mc > 0 else float("nan"),
                     "sign_first_half": float(np.sign(dd[:h].mean())) if h else 0.0, "sign_second_half": float(np.sign(dd[h:].mean()))}
        ps[side] = perm_p(dd); pr[side] = perm_p(-dd)
    hp = holm(ps)
    for side in ("high", "low"):
        res[side]["p_better"] = round(ps[side], 4); res[side]["p_better_holm"] = round(hp[side], 4); res[side]["p_worse"] = round(pr[side], 4)
    passing = [s for s in ("high", "low") if res[s]["p_better_holm"] < 0.05 and res[s]["gain_pct"] >= 3.0 and res[s]["sign_first_half"] == res[s]["sign_second_half"] == 1.0]
    not_worse = all(res[s]["gain_pct"] > -3.0 for s in ("high", "low"))
    dropped = [s for s in ("high", "low") if res[s]["gain_pct"] <= -3.0 and res[s]["p_worse"] < 0.05]
    res["verdict"] = "ADOPT (waits for the user's go-ahead)" if (passing and not_worse) else ("DROP the challenger" if dropped else "not demonstrated (the champion stays)")
    return res


def noharm(E: pd.DataFrame) -> dict:
    E = E.iloc[:LOOKS[0]]
    out = {"n_sessions": len(E)}
    for side, c, x in (("high", "ec_h", "ex_h"), ("low", "ec_l", "ex_l")):
        mc, mx = float(E[c].mean()), float(E[x].mean())
        out[side] = {"mean_ae_champion": round(mc, 3), "mean_ae_challenger": round(mx, 3), "challenger_worse_by_10pct_or_more": bool(mx >= 1.10 * mc)}
    return out


def update_c1() -> list[str]:
    lines = []
    d = build_dataset()
    E = eligible_sessions(d)
    w, w3 = frozen_w() if WFILE.exists() else (None, None)
    ident = (w == 0 and w3 == 0)
    n_read = 0 if d.empty else len(d)
    lines.append(f"Challenger (v2 clone, C1 next-hour columns), results LOCKED: {n_read} scored paired readings over {0 if d.empty else d.date.nunique()} session(s); {len(E)} eligible session(s) ({MIN_READINGS}+ scored readings) of the {LOOKS[1]} needed for the first decision "
                 f"({LOOKS[0]} for the no-harm check; pre-registered, research/hl/I_challenger.md); w (C1) = {w}, w3 (C3) = {w3}." + (" Both weights are 0: the challenger is identical to the champion, nothing to compare." if ident else " No error comparison is printed before the 10-session look."))
    if ident or len(E) < LOOKS[0]:
        return lines
    f10 = DIR / "analysis_n10.json"
    if not f10.exists():
        r = noharm(E); f10.write_text(json.dumps(r, indent=1))
        lines.append(f"Challenger no-harm look ({LOOKS[0]} eligible sessions; no p-value, no adoption possible): " + json.dumps(r))
    decided = False
    for nl in (LOOKS[1], LOOKS[2]):
        fn = DIR / f"analysis_n{nl}.json"
        if fn.exists():
            decided = decided or not json.loads(fn.read_text())["verdict"].startswith("not demonstrated")
            continue
        if len(E) >= nl and not decided:
            r = compare(E, nl); fn.write_text(json.dumps(r, indent=1))
            lines.append(f"Challenger pre-registered analysis at {nl} eligible sessions: " + json.dumps(r))
            decided = not r["verdict"].startswith("not demonstrated")
    return lines


# ------------------------------------------------------------------ C2: the pre-open order book (recorded; forward lead test H_B)
def final_snapshot(day: str) -> dict | None:
    f = Path(f"results/hl4_log/preopen_{day}.jsonl.gz")
    if not f.exists():
        return None
    for r in (json.loads(l) for l in gzip.open(f, "rt")):
        for x in r["payload"].get("rows", []):
            if x.get("metadata", {}).get("symbol") != "BSE":
                continue
            p = x["detail"]["preOpenMarket"]; st = p.get("lastUpdateTime", "")
            try:
                d = dt.datetime.strptime(st, "%d-%b-%Y %H:%M:%S")
            except ValueError:
                continue
            if d.strftime("%Y-%m-%d") != day or (d.hour, d.minute) < (9, 8):
                continue
            if float(p.get("finalPrice") or 0) > 0 and float(p.get("finalQuantity") or 0) > 0:
                b, s = float(p["totalBuyQuantity"]), float(p["totalSellQuantity"])
                iep, pc = float(p["IEP"]), float(p["prevClose"])
                return {"date": day, "stamp": st, "buy_qty": b, "sell_qty": s, "imbalance": round((b - s) / (b + s), 5) if b + s > 0 else float("nan"), "iep": iep, "prev_close": pc, "gap_pct": round(100 * math.log(iep / pc), 4)}
    return None


def update_book() -> None:
    old = pd.read_csv(BOOK) if BOOK.exists() else pd.DataFrame(columns=["date", "stamp", "buy_qty", "sell_qty", "imbalance", "iep", "prev_close", "gap_pct"])
    have = set(old.date.astype(str))
    new = []
    for f in sorted(Path("results/hl4_log").glob("preopen_*.jsonl.gz")):
        day = f.name[len("preopen_"):len("preopen_") + 10]
        if day < FIRST_SESSION or day in have:
            continue
        s = final_snapshot(day)
        if s:
            new.append(s)
    if new:
        DIR.mkdir(parents=True, exist_ok=True)
        pd.concat([old, pd.DataFrame(new)]).sort_values("date").to_csv(BOOK, index=False)


def official_bars() -> pd.DataFrame:
    d = pd.read_csv("data/processed/bse_daily.csv", index_col=0, parse_dates=True)
    e = Path("data/processed/bse_daily_extra.csv")
    if e.exists():
        x = pd.read_csv(e, index_col=0, parse_dates=True); d = pd.concat([d, x[~x.index.isin(d.index)]])
    d.index = d.index.strftime("%Y-%m-%d")
    return d


def update_c2() -> str:
    update_book()
    b = pd.read_csv(BOOK) if BOOK.exists() else pd.DataFrame()
    if b.empty:
        return "Challenger C2 (pre-open order book, recorded only, forward lead test H_B, results LOCKED): 0 sessions recorded."
    bars = official_bars()
    b = b[(b.date.isin(bars.index)) & (~b.date.isin(SPECIAL))].copy()
    b["R"] = [100 * math.log(bars.loc[d, "close"] / bars.loc[d, "open"]) for d in b.date]
    line = f"Challenger C2 (pre-open order book, recorded only, forward lead test H_B, results LOCKED): {len(b)} eligible session(s) of the {HB_LOOKS[0]} needed for the first analysis; no slope is computed before then."
    for nl in HB_LOOKS:
        fn = DIR / f"analysis_hb_n{nl}.json"
        if len(b) >= nl and not fn.exists():
            bb = b.sort_values("date").iloc[:nl]
            sl, p = slope_perm_p(bb.imbalance.values, bb.R.values)
            r = {"n_sessions": nl, "slope_pp_per_unit_I": round(sl, 3), "p_one_sided": round(p, 4), "note": "a lead only; applying it to any forecast needs its own registration"}
            fn.write_text(json.dumps(r, indent=1)); line += f"  Pre-registered H_B analysis at {nl} sessions: " + json.dumps(r)
            break
    return line


def update() -> None:
    for ln in update_c1():
        print(ln)
    print(update_c2())


# ------------------------------------------------------------------ self-test (synthetic data; must pass before the code is allowed to run on forward data)
def selftest() -> None:
    rng = np.random.default_rng(7)
    ok = True

    def check(name, cond):
        nonlocal ok
        print(("PASS  " if cond else "FAIL  ") + name); ok &= bool(cond)

    # 1. w = 0 reproduces the champion's pool exactly on real history
    S = HT.load_sessions(); ev, _ = LN.profile(S)
    zh0, zl0 = HT.zpool(S, ev); zh1, zl1 = pool_z(S, ev, 0.0)
    check("w=0 pool identical to the champion's", np.allclose(zh0, zh1) and np.allclose(zl0, zl1))
    # 2. no look-ahead: scale2 at checkpoint k does not change when later bars are scrambled
    s = S[-1]; k = 8
    r2a = float(np.nansum(s["r"][:k] ** 2)); r2 = s["r"].copy(); r2[k:] = rng.normal(0, 0.05, len(r2) - k)
    check("scale2 at k uses only bars before k", abs(r2a - float(np.nansum(r2[:k] ** 2))) < 1e-15)
    # 3. the scale clip
    check("scale2 clipped to [0.5, 2.0]", scale2(0.01, 1.0) == 0.5 and scale2(50.0, 1.0) == 2.0 and scale2(3.0, 0.0) == 1.0)
    # 4. permutation test: no difference -> large p; real gain -> small p; Holm
    null = rng.normal(0, 1, 40); gain = rng.normal(0.6, 1, 40)
    check("null difference: one-sided p > 0.1", perm_p(null) > 0.1)
    check("real gain: one-sided p < 0.01", perm_p(gain) < 0.01)
    hp = holm({"high": 0.01, "low": 0.04}); check("Holm: 0.01 -> 0.02, 0.04 -> 0.04", abs(hp["high"] - 0.02) < 1e-12 and abs(hp["low"] - 0.04) < 1e-12)
    # 5. decision logic on synthetic session tables
    n = 40
    base = rng.uniform(8, 12, n)
    E_same = pd.DataFrame({"date": [f"d{i:02d}" for i in range(n)], "n": 7, "ec_h": base, "ex_h": base, "ec_l": base, "ex_l": base})
    check("identical models: not demonstrated", compare(E_same, n)["verdict"].startswith("not demonstrated"))
    E_better = E_same.assign(ex_h=base * 0.85 + rng.normal(0, 0.1, n), ex_l=base * 0.85 + rng.normal(0, 0.1, n))
    check("clearly better challenger: ADOPT", compare(E_better, n)["verdict"].startswith("ADOPT"))
    E_worse = E_same.assign(ex_h=base * 1.2 + rng.normal(0, 0.1, n), ex_l=base * 1.2 + rng.normal(0, 0.1, n))
    check("clearly worse challenger: DROP", compare(E_worse, n)["verdict"].startswith("DROP"))
    E_one = E_same.assign(ex_h=base * 0.85 + rng.normal(0, 0.1, n), ex_l=base * 1.05)
    check("better on one side, 5% worse on the other: not adopted", not compare(E_one, n)["verdict"].startswith("ADOPT"))
    # 6. the H_B slope test
    x = rng.normal(0, 0.1, 60); y = 10 * x + rng.normal(0, 2.3, 60); sl, p = slope_perm_p(x, y)
    check("H_B slope test sees a strong planted slope", sl > 0 and p < 0.2)
    x2 = rng.normal(0, 0.1, 60); sl2, p2 = slope_perm_p(x2, rng.normal(0, 2.3, 60)); check("H_B slope test: pure noise gives a large p", p2 > 0.05)
    # 7. the fit can find a real volatility effect: synthetic sessions whose vol level persists through the day
    prof = LN.profile(S)[0]
    Ssyn = []
    for i in range(30):
        lvl = math.exp(rng.normal(0, 0.45)); r = rng.normal(0, 1, NB) * np.sqrt(prof) * lvl
        c = 3000 * np.exp(np.cumsum(r)); hh = c * np.exp(np.abs(rng.normal(0, 0.002, NB))); ll = c * np.exp(-np.abs(rng.normal(0, 0.002, NB)))
        Ssyn.append({"date": f"s{i:02d}", "h": hh, "l": ll, "c": c, "cf": c, "r": r, "has24": True})
    Fsyn = fit_w(Ssyn, grid=(0.0, 0.5, 1.0)); wsyn, tab = choose_w(Fsyn)
    check("planted persistence: the fit chooses w > 0", wsyn > 0)
    Snull = []
    for i in range(30):
        r = rng.normal(0, 1, NB) * np.sqrt(prof); c = 3000 * np.exp(np.cumsum(r)); hh = c * np.exp(np.abs(rng.normal(0, 0.002, NB))); ll = c * np.exp(-np.abs(rng.normal(0, 0.002, NB)))
        Snull.append({"date": f"n{i:02d}", "h": hh, "l": ll, "c": c, "cf": c, "r": r, "has24": True})
    wnull, _ = choose_w(fit_w(Snull, grid=(0.0, 0.5, 1.0)))
    check("no persistence: the fit keeps w = 0", wnull == 0.0)
    print("SELF-TEST " + ("PASSED" if ok else "FAILED")); sys.exit(0 if ok else 1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fit", action="store_true"); ap.add_argument("--write", action="store_true"); ap.add_argument("--update", action="store_true"); ap.add_argument("--selftest", action="store_true"); ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    elif a.fit:
        S = [x for x in HT.load_sessions() if x["date"] < FIRST_SESSION]
        DIR.mkdir(parents=True, exist_ok=True); chosen = {}
        sI = sigma_I_map(FIRST_SESSION)
        for mode, key in (("c1", "w"), ("c3", "w3")):
            F = fit_w(S, mode=mode, sI=sI); w, tab = choose_w(F); chosen[key] = w
            tab.to_csv(DIR / f"fit_{mode}.csv")
            print(f"[{mode.upper()}] {len(S)} sessions (through {S[-1]['date']}), {len(F) // len(GRID)} checkpoints per weight; pooled mean pinball (rupees) and mean absolute error of the median:"); print(tab.to_string()); print(f"[{mode.upper()}] chosen weight = {w}")
            d0 = F[F.w == 0.0].groupby("date")[["ae_high", "ae_low"]].mean(); dw = F[F.w == w].groupby("date")[["ae_high", "ae_low"]].mean()
            if w > 0:
                dd = (d0 - dw); print("      session-level paired difference AE(champion) - AE(challenger): mean/sd high %.3f/%.3f, low %.3f/%.3f (rupees, n=%d sessions)" % (dd.ae_high.mean(), dd.ae_high.std(), dd.ae_low.mean(), dd.ae_low.std(), len(dd)))
        if a.write:
            sha = hashlib.sha256(Path("research/hl/I_challenger.md").read_bytes()).hexdigest()
            WFILE.write_text(json.dumps({"w": chosen["w"], "w3": chosen["w3"], "grid": list(GRID), "rule": "research/hl/I_challenger.md 0.3 and 2: pooled pinball, >=1% better than weight 0", "fitted_on_sessions_through": S[-1]["date"], "n_sessions": len(S), "doc_sha256_when_frozen": sha}, indent=1))
            print(f"weights frozen -> {WFILE}")
    elif a.update or a.status:
        update()

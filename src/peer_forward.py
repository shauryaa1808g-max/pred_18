"""Forward test H (peer-move column): dataset, LOCKED report, the pre-registered analysis, and its self-test.  Definitions and rules: research/hl/H_peer_forward.md (frozen before any forward data).

  python3 src/peer_forward.py              # rebuild results/peer_forward/dataset.csv from results/hourly_table_log.jsonl and print counts + data-quality facts ONLY
  python3 src/peer_forward.py --selftest   # run the analysis code on SYNTHETIC data (null and a built-in effect) to prove it works; touches no forward data

LOCKED: before 60 eligible sessions exist no slope, correlation, p-value or plot of R on G is computed on forward data.  When the 60th eligible session arrives, the first analysis runs ONCE
on exactly the first 60 eligible sessions (results/peer_forward/analysis_n60.json); if it is not an adoption, one more analysis runs once at 120 (analysis_n120.json).  No other looks.
Called after the close from `hourly_table.py --score` (the 16:45 job), once the official close is in data/processed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

LOG = "results/hourly_table_log.jsonl"
OUT = Path("results/peer_forward")
DATASET = OUT / "dataset.csv"
STAGES = (60, 120)
SEED = 20261022
N_PERM = 20000
EXCLUDED_DATES = {"2026-11-08"}                        # Diwali Muhurat evening session; any weekend date (special Saturday/Sunday session) is excluded in code
PRIMARY_FROM, PRIMARY_TO = "11:00", "13:00"            # first live reading at or after 11:00 and before 13:00 IST
TRAIN_MIN = 30                                         # sessions used to fit the slope before the first out-of-sample prediction
MAE_GAIN_MIN = 0.03


def official_close() -> dict:
    fr = [pd.read_csv(f, usecols=["date", "close"]) for f in ("data/processed/bse_daily.csv", "data/processed/bse_daily_extra.csv") if Path(f).exists()]
    d = pd.concat(fr).drop_duplicates("date", keep="last").set_index("date")["close"]
    return d.to_dict()


def build_dataset() -> pd.DataFrame:
    oc = official_close()
    rows = []
    for l in Path(LOG).read_text().splitlines() if Path(LOG).exists() else []:
        if not l.strip():
            continue
        r = json.loads(l)
        pe = r.get("peers")
        if r.get("mode") != "live" or pe is None:
            continue
        sy = pe.get("symbols") or {}
        P, S = pe.get("P") or {}, pe.get("S") or {}
        row = {"date": r["date"], "asof": r["asof"], "price_now": r["price_now"], "error": pe.get("error", ""), "bse_move_pct": pe.get("bse_move_pct"),
               "P_valid": bool(P.get("valid")), "P_move_pct": P.get("move_pct"), "P_n_ok": P.get("n_ok"), "S_valid": bool(S.get("valid")), "S_move_pct": S.get("move_pct"), "S_n_ok": S.get("n_ok"),
               "G_P_pp": pe.get("gap_P_pp"), "G_S_pp": pe.get("gap_S_pp"), "nifty_move_pct": (sy.get("NIFTY") or {}).get("move_pct")}
        for n, v in sy.items():
            row[f"status_{n}"] = v.get("status")
        c = oc.get(r["date"])
        row["official_close"] = c
        row["R_pct"] = None if c is None else round(100 * math.log(c / r["price_now"]), 4)
        d = dt.date.fromisoformat(r["date"])
        row["normal_session"] = d.weekday() < 5 and r["date"] not in EXCLUDED_DATES
        row["in_primary_window"] = PRIMARY_FROM <= r["asof"] < PRIMARY_TO
        rows.append(row)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.sort_values(["date", "asof"]).reset_index(drop=True)
    first = df[df.in_primary_window].groupby("date").head(1).index                     # the first live reading in the window, per session
    df["primary"] = False; df.loc[first, "primary"] = True
    df["eligible"] = df.primary & df.P_valid & df.R_pct.notna() & df.normal_session
    return df


def eligible_sessions(df: pd.DataFrame) -> pd.DataFrame:
    return df[df.eligible].sort_values("date").reset_index(drop=True) if len(df) else df


# ------------------------------------------------------------------ the pre-registered analysis (runs only at 60 / 120, or on synthetic data in --selftest)
def slope(G: np.ndarray, R: np.ndarray) -> float:
    g = G - G.mean()
    return float((g * (R - R.mean())).sum() / (g * g).sum())


def perm_p(G: np.ndarray, R: np.ndarray, rng: np.random.Generator) -> float:
    """one-sided permutation p-value for slope > 0: G is permuted across sessions."""
    g = G - G.mean(); r = R - R.mean(); den = (g * g).sum(); obs = (g * r).sum() / den
    idx = np.argsort(rng.random((N_PERM, len(g))), axis=1)
    perm = (g[idx] * r).sum(axis=1) / den
    return float((1 + (perm >= obs).sum()) / (1 + N_PERM))


def holm(ps: list[float]) -> list[float]:
    m = len(ps); order = np.argsort(ps); adj = [0.0] * m; run = 0.0
    for k, i in enumerate(order):
        run = max(run, min(1.0, (m - k) * ps[i])); adj[i] = run
    return adj


def oos_mae(P: np.ndarray, G: np.ndarray, C: np.ndarray, train_min: int = TRAIN_MIN) -> dict:
    """expanding-window out-of-sample test: slope fitted (with intercept) on the sessions before t, applied WITHOUT intercept: pin' = price now x exp(slope x G / 100); compared with 'price stays'."""
    e_base, e_shift = [], []
    for t in range(train_min, len(P)):
        b = slope(G[:t], 100 * np.log(C[:t] / P[:t]))
        e_base.append(abs(P[t] - C[t])); e_shift.append(abs(P[t] * math.exp(b * G[t] / 100) - C[t]))
    if not e_base:
        return {"n_oos": 0, "mae_stays": None, "mae_shifted": None, "gain": None}
    mb, ms = float(np.mean(e_base)), float(np.mean(e_shift))
    return {"n_oos": len(e_base), "mae_stays": round(mb, 3), "mae_shifted": round(ms, 3), "gain": round(1 - ms / mb, 4)}


def analyse(sP: pd.DataFrame, sS: pd.DataFrame | None, label: str) -> dict:
    """sP: eligible sessions (basket P) with columns G_P_pp, R_pct, price_now, official_close, date.  sS: the same sessions' basket-S gap (G_S_pp) where valid, else NaN rows dropped.  Returns the decision record."""
    rng = np.random.default_rng(SEED)
    b1 = slope(sP.G_P_pp.values.astype(float), sP.R_pct.values.astype(float)); p1 = perm_p(sP.G_P_pp.values.astype(float), sP.R_pct.values.astype(float), rng)
    ss = sS[sS.G_S_pp.notna()] if sS is not None else None
    if ss is not None and len(ss) >= 20:
        b2 = slope(ss.G_S_pp.values.astype(float), ss.R_pct.values.astype(float)); p2 = perm_p(ss.G_S_pp.values.astype(float), ss.R_pct.values.astype(float), rng)
    else:
        b2, p2 = None, 1.0
    adj = holm([p1, p2])
    oos = oos_mae(sP.price_now.values.astype(float), sP.G_P_pp.values.astype(float), sP.official_close.values.astype(float))
    h = len(sP) // 2
    b_first = slope(sP.G_P_pp.values[:h].astype(float), sP.R_pct.values[:h].astype(float)); b_second = slope(sP.G_P_pp.values[h:].astype(float), sP.R_pct.values[h:].astype(float))
    c1 = b1 > 0 and adj[0] < 0.05
    c2 = oos["gain"] is not None and oos["gain"] >= MAE_GAIN_MIN
    c3 = b_first > 0 and b_second > 0
    reverse = b1 < 0 and perm_p(-sP.G_P_pp.values.astype(float), sP.R_pct.values.astype(float), np.random.default_rng(SEED + 1)) < 0.05
    return {"stage": label, "n_sessions": int(len(sP)), "first_date": str(sP.date.iloc[0]), "last_date": str(sP.date.iloc[-1]),
            "H1_basket_P": {"slope": round(b1, 4), "p_one_sided": round(p1, 5), "p_holm": round(adj[0], 5)}, "H2_basket_S": {"n": None if ss is None else int(len(ss)), "slope": None if b2 is None else round(b2, 4), "p_one_sided": round(p2, 5), "p_holm": round(adj[1], 5)},
            "out_of_sample": oos, "slope_first_half": round(b_first, 4), "slope_second_half": round(b_second, 4),
            "conditions": {"1_slope_positive_and_holm_p_below_0.05": bool(c1), "2_out_of_sample_gain_at_least_3pct": bool(c2), "3_same_sign_in_both_halves": bool(c3)},
            "adopted_as_documented_lead": bool(c1 and c2 and c3), "reverse_sign_lead_recorded_not_adopted": bool(reverse),
            "note": "Adoption only promotes the column from context to a documented lead; any pin-point shift needs its own registration. 'Not adopted' means not demonstrated, not 'no relationship' (see power in H_peer_forward.md section 1)."}


def run_stage(el: pd.DataFrame, n_stage: int) -> dict | None:
    f = OUT / f"analysis_n{n_stage}.json"
    if f.exists() or len(el) < n_stage:
        return None
    sub = el.iloc[:n_stage]                                           # exactly the first n_stage eligible sessions (frozen sample)
    res = analyse(sub, sub, f"first analysis at {n_stage} eligible sessions")
    f.write_text(json.dumps(res, indent=1)); return res


def update(verbose: bool = True) -> dict:
    """Rebuild the dataset and print counts only (LOCKED); run the pre-registered analysis when a stage is reached for the first time."""
    OUT.mkdir(parents=True, exist_ok=True)
    df = build_dataset()
    if df.empty:
        msg = "Forward test H (peer column): no live readings with peers logged yet."
        if verbose: print(msg)
        return {"readings": 0, "sessions": 0, "eligible": 0}
    df.to_csv(DATASET, index=False)
    el = eligible_sessions(df)
    n_el = len(el)
    st = {c.replace("status_", ""): df[c].value_counts().to_dict() for c in df.columns if c.startswith("status_")}
    out = {"readings": int(len(df)), "sessions": int(df.date.nunique()), "primary_readings": int(df.primary.sum()), "eligible": int(n_el), "peer_status_counts": st}
    stage = None
    if (OUT / "analysis_n60.json").exists() and not (OUT / "analysis_n120.json").exists():
        a60 = json.loads((OUT / "analysis_n60.json").read_text())
        if not a60["adopted_as_documented_lead"]:
            stage = run_stage(el, 120)
    stage = run_stage(el, 60) or stage
    if verbose:
        miss = {k: v for k, v in st.items() if any(s != "ok" for s in v)}
        print(f"Forward test H (peer column), results LOCKED: {out['readings']} live readings with peers over {out['sessions']} session(s); {n_el} eligible session(s) of the {STAGES[0]} needed for the first analysis (pre-registered, research/hl/H_peer_forward.md). "
              f"No slope, correlation or p-value is computed before then." + (f"  Peer data problems so far: {json.dumps(miss)}." if miss else "  No peer data problems so far."))
        if stage:
            print("Pre-registered analysis ran now: " + json.dumps(stage))
    out["analysis_ran"] = stage
    return out


# ------------------------------------------------------------------ self-test on synthetic data (never on forward data)
def _synthetic(n: int, true_b: float, seed: int, sdG: float = 1.0, sdR: float = 1.35) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    G = rng.normal(0, sdG, n); R = true_b * G + rng.normal(0, np.sqrt(max(sdR ** 2 - (true_b * sdG) ** 2, 0.01)), n)
    P = rng.uniform(3200, 3500, n); C = P * np.exp(R / 100)
    return pd.DataFrame({"date": pd.date_range("2026-10-22", periods=n, freq="B").strftime("%Y-%m-%d"), "G_P_pp": G, "G_S_pp": G + rng.normal(0, 0.2, n), "R_pct": R, "price_now": P, "official_close": C})


def selftest() -> None:
    ok = True
    # 1. permutation p-value is roughly uniform under the null and holm is monotone
    ps = [perm_p(*(lambda d: (d.G_P_pp.values, d.R_pct.values))(_synthetic(60, 0.0, 100 + k)), np.random.default_rng(k)) for k in range(60)]
    frac = float(np.mean(np.array(ps) < 0.05)); print(f"null: share of p<0.05 in 60 synthetic runs = {frac:.2f} (expect about 0.05; allowed 0.00-0.15)"); ok &= frac <= 0.15
    hh = holm([0.01, 0.04]); print(f"holm([0.01,0.04]) = {hh} (expect [0.02, 0.04])"); ok &= abs(hh[0] - 0.02) < 1e-9 and abs(hh[1] - 0.04) < 1e-9
    # 2. rates over many synthetic datasets (single runs are luck): under the null the adoption rule must fire rarely, with a built-in effect (slope 0.6, G sd 1.0, 60 sessions) it must fire often
    def rate(true_b, runs, seed0):
        hits = 0
        for k in range(runs):
            d = _synthetic(60, true_b, seed0 + k); hits += analyse(d, d, "synthetic")["adopted_as_documented_lead"]
        return hits / runs
    r_null, r_eff = rate(0.0, 300, 1000), rate(0.6, 60, 5000)
    print(f"adoption rate: null {r_null:.3f} over 300 runs (expect about 0.01-0.03; allowed <= 0.06); slope 0.6 {r_eff:.2f} over 60 runs (the p-test alone has power ~0.98; the full three-condition rule costs about 20 points; allowed >= 0.65)")
    ok &= r_null <= 0.06 and r_eff >= 0.65
    d1 = _synthetic(60, 0.6, 7); r1 = analyse(d1, d1, "synthetic effect 0.6"); print("one effect run:", json.dumps({k: r1[k] for k in ("H1_basket_P", "out_of_sample", "conditions", "adopted_as_documented_lead")}))
    # 3. a reverse-sign effect is recorded but never adopted
    dr = _synthetic(60, -0.6, 9); rr = analyse(dr, dr, "synthetic reverse"); print("reverse    :", json.dumps({k: rr[k] for k in ("H1_basket_P", "adopted_as_documented_lead", "reverse_sign_lead_recorded_not_adopted")}))
    ok &= rr["adopted_as_documented_lead"] is False and rr["reverse_sign_lead_recorded_not_adopted"] is True
    # 4. the out-of-sample step uses only earlier sessions: shuffling the FUTURE rows must not change the prediction for session t
    P, G, C = d1.price_now.values, d1.G_P_pp.values, d1.official_close.values
    t = 40; b_a = slope(G[:t], 100 * np.log(C[:t] / P[:t])); G2, C2, P2 = G.copy(), C.copy(), P.copy(); perm = np.r_[np.arange(t + 1), np.random.default_rng(1).permutation(np.arange(t + 1, 60))]
    G2, C2, P2 = G[perm], C[perm], P[perm]; b_b = slope(G2[:t], 100 * np.log(C2[:t] / P2[:t])); print(f"no look-ahead: slope before session {t} unchanged by shuffling later sessions: {b_a:.6f} vs {b_b:.6f}"); ok &= abs(b_a - b_b) < 1e-12
    # 5. the dataset builder, locked report and stage gate on a synthetic log in a scratch folder
    import os, tempfile
    cwd = os.getcwd(); tmp = tempfile.mkdtemp()
    try:
        os.chdir(tmp); Path("data/processed").mkdir(parents=True); Path("results").mkdir()
        dates = pd.bdate_range("2026-10-22", periods=62).strftime("%Y-%m-%d"); rng = np.random.default_rng(3); lines, oc = [], []
        for d in dates:
            P = float(rng.uniform(3200, 3400)); C = P * float(np.exp(rng.normal(0, 0.012)))
            sym = {n: {"status": "ok", "move_pct": float(rng.normal(0, 1))} for n in ("CDSL", "MCX", "MOTILALOFS", "IEX", "ANGELONE", "NIFTY", "BANKNIFTY")}
            pe = {"bse_move_pct": 0.5, "symbols": sym, "P": {"valid": True, "move_pct": 0.1, "n_ok": 4, "n_of": 4}, "S": {"valid": True, "move_pct": 0.2, "n_ok": 3, "n_of": 3}, "gap_P_pp": float(rng.normal(0, 1)), "gap_S_pp": float(rng.normal(0, 1))}
            lines.append(json.dumps({"date": d, "asof": "11:16", "mode": "live", "price_now": P, "peers": pe})); oc.append({"date": d, "close": C})
        Path("results/hourly_table_log.jsonl").write_text("\n".join(lines) + "\n"); pd.DataFrame(oc).to_csv("data/processed/bse_daily_extra.csv", index=False)
        sys.stdout.flush()
        r = update(verbose=False)
        ok &= r["eligible"] == 62 and Path("results/peer_forward/analysis_n60.json").exists() and not Path("results/peer_forward/analysis_n120.json").exists()
        a = json.loads(Path("results/peer_forward/analysis_n60.json").read_text()); ok &= a["n_sessions"] == 60 and a["last_date"] == dates[59]
        print(f"gate: 62 synthetic eligible sessions -> analysis ran once on exactly the first 60 (last date {a['last_date']}); n120 not run yet: {not Path('results/peer_forward/analysis_n120.json').exists()}")
        before = Path("results/peer_forward/analysis_n60.json").read_text(); update(verbose=False); ok &= before == Path("results/peer_forward/analysis_n60.json").read_text()
    finally:
        os.chdir(cwd)
    print("SELFTEST", "PASSED" if ok else "FAILED"); sys.exit(0 if ok else 1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    selftest() if a.selftest else update()

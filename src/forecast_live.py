"""Live next-session forecast.  Refits the pre-registered selected models on ALL data through the last published session and forecasts t = n.

Selected models (pre-registered gate, results/eval_scale_all.csv):  R -> S6,  G -> S4,  I -> S6,  rho -> HAR.   Location: L0 (no model passed its gate).

Usage: python3 src/forecast_live.py [--provisional "open,high,low,close,volume"] [--out results/forecast_record_2026-10-14.json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

import models as P
from common import EPS, GRID, load_bse, load_index, targets

TARGET_SESSION = "2026-10-14"
SELECT = {"R": "S6", "G": "S4", "I": "S6"}


def sha(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def live_sigma(x: np.ndarray, v: np.ndarray, model: str) -> np.ndarray:
    """sigma path with the final entry = forecast for the next (unseen) session; parameters estimated on all n known observations."""
    n = len(x)
    xe, ve = np.append(x, 0.0), np.append(v, EPS)       # placeholders at index n are never read by sigma[n]
    if model == "S0":
        return P.sigma_hist(xe)
    if model == "S1":
        return P.sigma_ewma(xe)
    if model in ("S2", "S3"):
        s, par, ok = P.sigma_garch_block(xe, n, model == "S3", None)
        if not ok:
            print(f"WARNING: GARCH fit failed for {model}; EWMA fallback")
        return s
    if model == "S4":
        return P.sigma_har_block(ve, n)
    if model == "S6":
        return np.sqrt(live_sigma(x, v, "S2") * live_sigma(x, v, "S4"))
    raise ValueError(model)


def quantiles(x, sig, n):
    xe = np.append(x, 0.0)
    return P.fhs_quantiles(xe, sig, n, center=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provisional", default=None, help="open,high,low,close,volume for 2026-10-13 if the official file is not yet published")
    ap.add_argument("--out", default="results/forecast_record_2026-10-14.json")
    a = ap.parse_args()
    d = load_bse()
    provisional = False
    last = pd.Timestamp("2026-10-13")
    if d.index[-1] < last:
        if not a.provisional:
            raise SystemExit("official 2026-10-13 row missing; pass --provisional to run on unofficial numbers")
        o, h, l, c, vol = [float(z) for z in a.provisional.split(",")]
        row = pd.DataFrame({"prev": [d["close"].iloc[-1]], "open": [o], "high": [h], "low": [l], "close": [c], "vol": [vol]}, index=[last])
        d = pd.concat([d, row])
        provisional = True
    t = targets(d)
    n = len(d)
    P0 = float(d["close"].iloc[-1])
    x = {k: t[k].values for k in ("R", "G", "I")}
    v = {"R": t["v"].values, "G": np.clip(t["G"].values ** 2, EPS, None), "I": t["gk"].values}
    out: dict = {"stock": "BSE Ltd", "ticker": "NSE:BSE", "isin": "INE118H01025", "currency": "INR", "exchange_tz": "Asia/Kolkata",
                 "target_session": TARGET_SESSION, "data_last_session": str(d.index[-1].date()), "n_sessions": n,
                 "reference_price_P0": P0, "reference_price_status": "PROVISIONAL (Google Finance/stockanalysis 15:30 IST)" if provisional else "OFFICIAL NSE close (sec_bhavdata_full)",
                 "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "selected_models": SELECT | {"rho": "HAR"}, "location_model": "L0 (no model passed its pre-registered gate)"}
    # ---- scale forecasts for all candidates (transparency) and quantiles for the selected one
    sig_table = {}
    for tgt in ("R", "G", "I"):
        sig_table[tgt] = {}
        for m in ("S0", "S1", "S2", "S3", "S4", "S6"):
            s = live_sigma(x[tgt], v[tgt], m)
            sig_table[tgt][m] = float(s[n])
    out["sigma_forecasts_by_model"] = sig_table
    qtab = {}
    zsel = {}
    for tgt, m in SELECT.items():
        s = live_sigma(x[tgt], v[tgt], m)
        q = quantiles(x[tgt], s, n)
        qtab[tgt] = {f"q{g:g}": float(z) for g, z in zip(GRID, q)}
        qtab[tgt]["sigma"] = float(s[n])
        lo = max(0, n - P.Z_WINDOW)
        z = x[tgt][lo:n] / s[lo:n]
        zsel[tgt] = z[np.isfinite(z)]
    # ---- range model
    rho = t["rho"].values
    sr = P.sigma_har_block(np.append(np.clip(rho ** 2, EPS, None), EPS), n)
    qrho = P.fhs_quantiles(np.append(rho, 0.0), sr, n, center=False)
    qtab["rho"] = {f"q{g:g}": float(z) for g, z in zip(GRID, qrho)} | {"sigma": float(sr[n])}
    out["log_return_quantiles"] = qtab
    # ---- price-level translation
    out["price_quantiles"] = {k: {kk: round(P0 * float(np.exp(vv)), 2) for kk, vv in q.items() if kk != "sigma"} for k, q in qtab.items() if k in ("R", "G", "I")}
    out["price_quantiles"]["rho_pct_of_price"] = {kk: round(100 * (float(np.exp(vv)) - 1), 2) for kk, vv in qtab["rho"].items() if kk != "sigma"}
    # ---- joint OHLC bootstrap using the selected R-model sigma path (exploratory, evaluated in results via src/eval_hl.py)
    sR = live_sigma(x["R"], v["R"], SELECT["R"])
    lo = max(0, n - P.Z_WINDOW)
    U = t[["G", "Hp", "Lp", "R"]].values[lo:n] / sR[lo:n, None]
    U = U[np.isfinite(U).all(axis=1)]
    draws = sR[n] * U
    hl = {}
    for j, k in enumerate(["G", "Hp", "Lp", "R"]):
        hl[k] = {f"q{g:g}": float(np.quantile(draws[:, j], GRID)[i]) for i, g in enumerate(GRID)}
    out["ohlc_bootstrap_log_quantiles"] = hl
    out["ohlc_bootstrap_price_quantiles"] = {k: {kk: round(P0 * float(np.exp(vv)), 2) for kk, vv in q.items()} for k, q in hl.items() if k in ("Hp", "Lp")}
    out["ohlc_bootstrap_probabilities"] = {
        "P(high > P0)": float((draws[:, 1] > 0).mean()), "P(low < P0)": float((draws[:, 2] < 0).mean()),
        "P(high > P0*1.02)": float((draws[:, 1] > np.log(1.02)).mean()), "P(low < P0*0.98)": float((draws[:, 2] < np.log(0.98)).mean()),
        "P(high>P0*1.03)": float((draws[:, 1] > np.log(1.03)).mean()), "P(low<P0*0.97)": float((draws[:, 2] < np.log(0.97)).mean()),
        "n_draws": int(len(draws)),
    }
    # ---- probabilities for the selected R model (location 0, i.e. median-centred standardised residuals)
    zc = zsel["R"] - np.median(zsel["R"])
    sRn = qtab["R"]["sigma"]
    out["probabilities"] = {
        "P(close>P0) [L0 by construction, NOT a validated directional claim]": 0.5,
        "P(close>P0) using un-centred empirical residuals (includes historical drift)": float((zsel["R"] > 0).mean()),
        "P(|R|<0.25*sigma_R) 'broadly unchanged'": float((np.abs(zc) < 0.25).mean()),
        "P(|R|<0.5%)": float((np.abs(sRn * zc) < 0.005).mean()), "P(|R|<1%)": float((np.abs(sRn * zc) < 0.01).mean()),
        "P(R>+2%)": float((sRn * zc > 0.02).mean()), "P(R<-2%)": float((sRn * zc < -0.02).mean()),
        "P(R>+4%)": float((sRn * zc > 0.04).mean()), "P(R<-4%)": float((sRn * zc < -0.04).mean()),
        "note": "probabilities are model-based on the trailing 500 standardised residuals; 90% interval coverage was validated (Final-window Kupiec p=0.27), the tail/centre masses are not separately validated",
    }
    base_rates = {}
    R = t["R"]
    base_rates["share_up_all"] = float((R > 0).mean())
    base_rates["share_up_last_565"] = float((R.iloc[-565:] > 0).mean())
    base_rates["share_up_last_60"] = float((R.iloc[-60:] > 0).mean())
    base_rates["share_up_wednesdays"] = float((R[R.index.dayofweek == 2] > 0).mean())
    out["unconditional_up_frequencies"] = base_rates
    # ---- implied-vol cross-check (exploratory)
    ivp = Path("data/processed/bse_iv_daily.csv")
    if ivp.exists():
        iv = pd.read_csv(ivp, parse_dates=["date"]).set_index("date")["iv_atm"]
        out["implied_vol_crosscheck"] = {"last_iv_date": str(iv.index[-1].date()), "iv_atm_annual": float(iv.iloc[-1]), "implied_daily_sigma": float(iv.iloc[-1] / np.sqrt(252)),
                                          "model_sigma_R": sRn}
    # ---- provenance
    try:
        out["code_commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:  # noqa: BLE001
        out["code_commit"] = "unknown"
    out["data_sha256_16"] = {p: sha(p) for p in ("data/processed/bse_daily.csv", "data/processed/index_daily.csv", "data/corp_actions_verified.csv")}
    out["last_bar"] = {k: float(d[k].iloc[-1]) for k in ("open", "high", "low", "close", "vol")}
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("reference_price_P0", "reference_price_status", "sigma_forecasts_by_model")}, indent=1))
    pq = out["price_quantiles"]
    print("\nPrice quantiles (INR) for 14-Oct-2026:")
    print(pd.DataFrame({k: pq[k] for k in ("G", "I", "R")}).T.to_string())
    print("\nOHLC-bootstrap high / low price quantiles:"); print(pd.DataFrame(out["ohlc_bootstrap_price_quantiles"]).T.to_string())
    print("\nrange (% of price):", out["price_quantiles"]["rho_pct_of_price"])
    print("\nprobabilities:"); [print(" ", k, round(v, 4) if isinstance(v, float) else v) for k, v in out["probabilities"].items()]
    print("\nOHLC prob:", {k: round(v, 3) for k, v in out["ohlc_bootstrap_probabilities"].items()})
    print("up-frequencies:", {k: round(v, 3) for k, v in base_rates.items()})
    print("IV cross-check:", out.get("implied_vol_crosscheck"))


if __name__ == "__main__":
    main()

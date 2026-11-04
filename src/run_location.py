"""Location-model selection (stage=dev) and evaluation (stage=full).

stage=dev : uses only sessions <= 2024-06-28 to pick ridge alpha and logit C (OOS MSE / log-loss), writes results/location_selection.json
stage=full: loads the frozen choices, evaluates L0..L3 on Validation / Final / pooled / regimes, group ablations, top-5-day robustness.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

import location as L
import metrics as M
import models as P
from common import load_bse, load_breadth, load_index, targets

RES = Path("results")
ALPHAS = [1, 10, 100, 1000]
CS = [0.01, 0.1, 1.0]
ALL_COLS = [c for g in L.GROUPS.values() for c in g]


def prep():
    d = load_bse(); t = targets(d); ix = load_index(); br = load_breadth()
    F, s = L.feature_frame(d, t, ix, br)
    R = t["R"].values
    y_std = R / s
    y_dir = (R > 0).astype(int)
    return d, t, F, s, R, y_std, y_dir


def expanding_mean(R: np.ndarray) -> np.ndarray:
    cs = np.cumsum(R)
    m = np.full(len(R), np.nan)
    idx = np.arange(1, len(R))
    m[idx] = cs[idx - 1] / idx
    return m


def stage_dev():
    d, t, F, s, R, y_std, y_dir = prep()
    n_end = int(np.searchsorted(d.index.values, np.datetime64(L.DEV_END), side="right"))
    ev = np.arange(P.MIN_HIST, n_end)
    ok = np.isfinite(y_std[ev]) & np.isfinite(s[ev])
    out = {"dev_end": str(L.DEV_END.date()), "n_eval": int(ok.sum()), "ridge": {}, "logit": {}}
    for a in ALPHAS:
        pr = L.walk(F, y_std, y_dir, ALL_COLS, alpha=a, C=None, t_end=n_end, kind="ridge")
        out["ridge"][str(a)] = float(np.mean((y_std[ev][ok] - pr[ev][ok]) ** 2))
    base = expanding_mean(R)
    out["ridge_bench_hist_mean_mse_std"] = float(np.mean((y_std[ev][ok] - (base[ev] / s[ev])[ok]) ** 2))
    out["ridge_bench_zero_mse_std"] = float(np.mean(y_std[ev][ok] ** 2))
    for c in CS:
        pr = L.walk(F, y_std, y_dir, ALL_COLS, alpha=0, C=c, t_end=n_end, kind="logit")
        p = np.clip(pr[ev][ok], 1e-6, 1 - 1e-6); yy = y_dir[ev][ok]
        out["logit"][str(c)] = float(-np.mean(yy * np.log(p) + (1 - yy) * np.log(1 - p)))
    out["best_alpha"] = int(min(ALPHAS, key=lambda a: out["ridge"][str(a)]))
    out["best_C"] = float(min(CS, key=lambda c: out["logit"][str(c)]))
    (RES / "location_selection.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


def window_mask(idx, lo, hi):
    m = np.ones(len(idx), bool)
    if lo: m &= idx >= pd.Timestamp(lo)
    if hi: m &= idx <= pd.Timestamp(hi)
    return m


def eval_loc(label, mask, d, R, s, mu_ridge, p_logit, bench_mean, drop_top5=False):
    idx = np.where(mask & np.isfinite(mu_ridge) & np.isfinite(p_logit))[0]
    if len(idx) < 30:
        return None
    if drop_top5:
        keep = np.argsort(-np.abs(R[idx]))[5:]
        idx = np.sort(idx[keep])
    y = R[idx]
    f0 = np.zeros(len(idx)); f1 = bench_mean[idx]; f2 = mu_ridge[idx] * s[idx]
    up = (y > 0).astype(int)
    p_up = up.mean(); base_acc = max(p_up, 1 - p_up)
    pred_r = (f2 > 0).astype(int); hits_r = int((pred_r == up).sum())
    pred_l = (p_logit[idx] > 0.5).astype(int); hits_l = int((pred_l == up).sum())
    cw_t, cw_p = M.clark_west(y, f2, f1)
    brier = float(np.mean((p_logit[idx] - up) ** 2)); brier_base = float(np.mean((p_up - up) ** 2))
    return {
        "window": label + ("|drop_top5" if drop_top5 else ""), "n": len(idx), "share_up": p_up,
        "oosR2_ridge_vs_histmean": M.oos_r2(y, f2, f1), "oosR2_ridge_vs_zero": M.oos_r2(y, f2, f0), "oosR2_histmean_vs_zero": M.oos_r2(y, f1, f0),
        "clark_west_t": cw_t, "clark_west_p": cw_p,
        "dir_acc_ridge": hits_r / len(idx), "dir_binom_p_ridge": M.binom_p(hits_r, len(idx), base_acc),
        "dir_acc_logit": hits_l / len(idx), "dir_binom_p_logit": M.binom_p(hits_l, len(idx), base_acc),
        "base_acc_best_constant": base_acc, "auc_logit": M.auc(up, p_logit[idx]),
        "brier_logit": brier, "brier_const": brier_base, "brier_skill": 1 - brier / brier_base,
        "mean_pred_up_prob": float(p_logit[idx].mean()),
    }


def stage_full():
    sel = json.loads((RES / "location_selection.json").read_text())
    a, C = sel["best_alpha"], sel["best_C"]
    d, t, F, s, R, y_std, y_dir = prep()
    idx = d.index
    mu_r = L.walk(F, y_std, y_dir, ALL_COLS, alpha=a, C=None, kind="ridge")
    p_l = L.walk(F, y_std, y_dir, ALL_COLS, alpha=0, C=C, kind="logit")
    bm = expanding_mean(R)
    windows = {
        "dev": (None, "2024-06-28"), "val": ("2024-07-01", "2025-06-30"), "final": ("2025-07-01", None),
        "valfinal": ("2024-07-01", None), "all": (None, None),
        "regime:pre-covid": (None, "2020-02-19"), "regime:covid": ("2020-02-20", "2020-12-31"), "regime:2021-22": ("2021-01-01", "2022-12-31"),
        "regime:2023": ("2023-01-01", "2023-12-31"), "regime:2024": ("2024-01-01", "2024-12-31"), "regime:2025+": ("2025-01-01", None),
    }
    rows = []
    start_ok = np.zeros(len(idx), bool); start_ok[P.MIN_HIST:] = True
    for lab, (lo, hi) in windows.items():
        m = window_mask(idx, lo, hi) & start_ok
        for drop in (False, True) if lab in ("valfinal", "final", "all") else (False,):
            r = eval_loc(lab, m, d, R, s, mu_r, p_l, bm, drop_top5=drop)
            if r: rows.append(r)
    ev = pd.DataFrame(rows)
    ev.to_csv(RES / "eval_location.csv", index=False)
    # group ablations on the pooled Validation+Final window and on the whole OOS sample
    abl = []
    for g, cols in list(L.GROUPS.items()) + [("all_features", ALL_COLS)]:
        pr = L.walk(F, y_std, y_dir, cols, alpha=a, C=None, kind="ridge")
        for lab in ("valfinal", "all"):
            lo, hi = windows[lab]
            m = window_mask(idx, lo, hi) & start_ok & np.isfinite(pr)
            ii = np.where(m)[0]
            y = R[ii]; f2 = pr[ii] * s[ii]; f1 = bm[ii]
            cw_t, cw_p = M.clark_west(y, f2, f1)
            up = (y > 0).astype(int); base = max(up.mean(), 1 - up.mean()); h = int(((f2 > 0).astype(int) == up).sum())
            abl.append({"group": g, "window": lab, "n": len(ii), "oosR2_vs_histmean": M.oos_r2(y, f2, f1), "cw_p": cw_p, "dir_acc": h / len(ii), "dir_p": M.binom_p(h, len(ii), base)})
    pd.DataFrame(abl).to_csv(RES / "eval_location_ablation.csv", index=False)
    # reliability table (logit P(up)) on valfinal
    m = window_mask(idx, "2024-07-01", None) & start_ok & np.isfinite(p_l)
    ii = np.where(m)[0]
    bins = pd.qcut(p_l[ii], 5, duplicates="drop")
    rel = pd.DataFrame({"p": p_l[ii], "up": (R[ii] > 0).astype(int), "bin": bins}).groupby("bin", observed=True).agg(n=("up", "size"), mean_p=("p", "mean"), freq_up=("up", "mean"))
    rel.to_csv(RES / "eval_location_reliability_valfinal.csv")
    pd.set_option("display.width", 250)
    print(ev.round(4).to_string(index=False)); print(pd.DataFrame(abl).round(4).to_string(index=False)); print(rel.round(3))
    # frozen outputs for the live forecast stage
    pd.DataFrame({"date": idx, "mu_ridge": mu_r * s, "p_up_logit": p_l, "s_ewma": s}).to_csv(RES / "location_predictions.csv", index=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["dev", "full"], required=True)
    a = ap.parse_args()
    RES.mkdir(exist_ok=True)
    stage_dev() if a.stage == "dev" else stage_full()

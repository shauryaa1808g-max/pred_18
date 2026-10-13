"""Location (mean / direction) models L1..L3 evaluated walk-forward against the zero-location benchmark L0.

Everything is built from information dated <= t-1 for target date t.  alpha / C are selected on the Development window only
(per docs/PREREGISTRATION.md) and then frozen.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

import models as P
from common import EPS, index_returns

DEV_END = pd.Timestamp("2024-06-28")
VAL_START, VAL_END = pd.Timestamp("2024-07-01"), pd.Timestamp("2025-06-30")
FIN_START = pd.Timestamp("2025-07-01")

GROUPS = {
    "momentum": ["r1", "r2", "cum5", "cum20", "cum60", "i1", "g1"],
    "market": ["nifty1", "capmkts1", "resid1", "dvix1", "vixpct", "adv1"],
    "technical": ["rsi14", "dist20", "dist50"],
    "calendar": ["dow1", "dow2", "dow3", "dow4"],
    "volume": ["turn_z"],
}


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    dlt = close.diff()
    up = dlt.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-dlt.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / (dn + EPS))


def feature_frame(d: pd.DataFrame, t: pd.DataFrame, ix: pd.DataFrame, br: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    """Feature row t uses only data dated <= t-1.  Returns (features, s) with s = EWMA sigma forecast for R_t (info <= t-1)."""
    R = t["R"]
    s = pd.Series(P.sigma_ewma(R.values), index=R.index)
    ir = index_returns(ix.reindex(d.index))
    nifty = ir["r_nifty50"]
    cap = ir["r_capmkts"] if "r_capmkts" in ir else pd.Series(np.nan, index=R.index)
    F = pd.DataFrame(index=R.index)
    # all raw quantities are shifted by one session so that row t only sees t-1 and earlier
    F["r1"] = R.shift(1) / s
    F["r2"] = R.shift(2) / s
    F["cum5"] = R.rolling(5).sum().shift(1) / (s * np.sqrt(5))
    F["cum20"] = R.rolling(20).sum().shift(1) / (s * np.sqrt(20))
    F["cum60"] = R.rolling(60).sum().shift(1) / (s * np.sqrt(60))
    F["i1"] = t["I"].shift(1) / s
    F["g1"] = t["G"].shift(1) / s
    F["nifty1"] = nifty.shift(1) / nifty.rolling(60).std().shift(1)
    F["capmkts1"] = (cap.shift(1) / cap.rolling(60).std().shift(1)).fillna(0.0)
    # rolling beta on data dated <= t-2 (strictly before the lagged residual's own day)
    cov = R.rolling(120).cov(nifty).shift(1)
    var = nifty.rolling(120).var().shift(1)
    beta = (cov / var).clip(-1, 4)
    F["resid1"] = (R.shift(1) - beta * nifty.shift(1)) / s
    lv = np.log(ix["vix_close"].reindex(d.index))
    F["dvix1"] = lv.diff().shift(1) / lv.diff().rolling(60).std().shift(1)
    F["vixpct"] = lv.shift(1).rolling(500, min_periods=120).rank(pct=True) - 0.5
    lt = np.log(d["turnover_cr"].clip(lower=EPS))
    F["turn_z"] = ((lt - lt.rolling(60).mean()) / lt.rolling(60).std()).shift(1)
    F["adv1"] = br["adv_share"].reindex(d.index).shift(1) - 0.5
    F["rsi14"] = rsi(d["close"]).shift(1) - 50
    ma20, ma50 = d["close"].rolling(20).mean(), d["close"].rolling(50).mean()
    F["dist20"] = np.log(d["close"] / ma20).shift(1) / (s * np.sqrt(20))
    F["dist50"] = np.log(d["close"] / ma50).shift(1) / (s * np.sqrt(50))
    dow = pd.Series(d.index.dayofweek, index=d.index)
    for k in range(1, 5):
        F[f"dow{k}"] = (dow == k).astype(float)
    F = F.replace([np.inf, -np.inf], np.nan)
    return F, s.values


def walk(F: pd.DataFrame, y_std: np.ndarray, y_dir: np.ndarray, cols: list[str], alpha: float, C: float | None,
         t_end: int | None = None, kind: str = "ridge") -> np.ndarray:
    """Block-refit expanding-window prediction for t in [MIN_HIST, t_end).  Returns standardised-mean (ridge) or P(up) (logit)."""
    n = len(F) if t_end is None else t_end
    X_all = F[cols].values
    out = np.full(n, np.nan)
    for b0 in range(P.MIN_HIST, n, P.REFIT):
        tr = np.arange(0, b0)
        ok = np.isfinite(X_all[tr]).all(axis=1) & np.isfinite(y_std[tr])
        tr = tr[ok]
        mu, sd = X_all[tr].mean(0), X_all[tr].std(0) + 1e-12
        Z = (X_all[tr] - mu) / sd
        blk = np.arange(b0, min(b0 + P.REFIT, n))
        Zb = np.nan_to_num((X_all[blk] - mu) / sd, nan=0.0)
        if kind == "ridge":
            yt = np.clip(y_std[tr], -5, 5)
            ym = yt.mean()
            A = Z.T @ Z + alpha * np.eye(Z.shape[1])
            w = np.linalg.solve(A, Z.T @ (yt - ym))
            out[blk] = ym + Zb @ w
        else:
            clf = LogisticRegression(C=C, max_iter=500)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                clf.fit(Z, y_dir[tr])
            out[blk] = clf.predict_proba(Zb)[:, 1]
    return out

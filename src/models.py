"""Scale models (S0..S6), filtered-historical-simulation quantiles and the walk-forward driver.

Conventions
* Arrays are indexed by session number t (0 = first session after the listing day).
* sigma[t] is the model's forecast of the scale of x[t] made with information x[:t] (and exogenous features dated <= t-1) only.
* A model with parameters is re-estimated at the start of every `REFIT`-session block using data strictly before the block;
  the filter is then run over the whole series so sigma[t] for t in the block uses only past realised values.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd

from common import EPS, GRID

REFIT = 20
MIN_HIST = 500        # sessions of history before the first forecast
Z_WINDOW = 500        # trailing standardised residuals used for quantiles
WARM = 30
GARCH_WIN = 1500


# ----------------------------------------------------------------------------- simple scale models
def sigma_hist(x: np.ndarray) -> np.ndarray:
    """S0: expanding RMS (zero-mean), no volatility timing."""
    n = len(x)
    cs = np.cumsum(x ** 2)
    s = np.full(n, np.nan)
    idx = np.arange(WARM, n)
    s[idx] = np.sqrt(cs[idx - 1] / idx)
    return s


def sigma_ewma(x: np.ndarray, lam: float = 0.94) -> np.ndarray:
    """S1: RiskMetrics EWMA on squared values."""
    n = len(x)
    s = np.full(n, np.nan)
    v = float(np.mean(x[:WARM] ** 2))
    for t in range(WARM, n):
        s[t] = np.sqrt(v)
        v = lam * v + (1 - lam) * x[t] ** 2
    return s


# ----------------------------------------------------------------------------- GARCH family
def _garch_filter(x_pct: np.ndarray, omega: float, alpha: float, beta: float, gamma: float, h0: float) -> np.ndarray:
    n = len(x_pct)
    h = np.empty(n)
    hp = h0
    for t in range(n):
        h[t] = hp
        e = x_pct[t]
        hp = omega + (alpha + (gamma if e < 0 else 0.0)) * e * e + beta * hp
    return np.sqrt(h)


def garch_fit(x: np.ndarray, t_b: int, gjr: bool) -> tuple[float, float, float, float] | None:
    from arch import arch_model

    lo = max(0, t_b - GARCH_WIN)
    y = x[lo:t_b] * 100.0
    am = arch_model(y, mean="Zero", vol="GARCH", p=1, o=1 if gjr else 0, q=1, dist="t")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            res = am.fit(disp="off", options={"maxiter": 400})
        except Exception:  # noqa: BLE001
            return None
    p = res.params
    omega, alpha, beta = float(p["omega"]), float(p["alpha[1]"]), float(p["beta[1]"])
    gamma = float(p["gamma[1]"]) if gjr else 0.0
    if not np.isfinite([omega, alpha, beta, gamma]).all() or omega <= 0 or alpha < 0 or beta < 0 or alpha + beta + gamma / 2 >= 1.0005:
        return None
    return omega, alpha, beta, gamma


def sigma_garch_block(x: np.ndarray, t_b: int, gjr: bool, prev: tuple | None) -> tuple[np.ndarray, tuple | None, bool]:
    par = garch_fit(x, t_b, gjr)
    ok = par is not None
    if par is None:
        par = prev
    if par is None:  # no valid fit yet: fall back to EWMA path (flagged)
        return sigma_ewma(x), None, False
    h0 = float(np.mean((x[:WARM] * 100.0) ** 2))
    s = _garch_filter(x * 100.0, *par, h0) / 100.0
    s[:WARM] = np.nan
    return s, par, ok


# ----------------------------------------------------------------------------- HAR
def har_design(v: np.ndarray, extra: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Regressors for log v[t], all dated <= t-1.  Returns (X with intercept, y); rows 0..21 are NaN."""
    n = len(v)
    s = pd.Series(v)
    d = np.log(s.shift(1).clip(lower=EPS))
    w = np.log(s.shift(1).rolling(5).mean().clip(lower=EPS))
    m = np.log(s.shift(1).rolling(22).mean().clip(lower=EPS))
    cols = [np.ones(n), d.values, w.values, m.values]
    if extra is not None:
        cols += [extra[:, j] for j in range(extra.shape[1])]
    X = np.column_stack(cols)
    y = np.log(np.clip(v, EPS, None))
    return X, y


def sigma_har_block(v: np.ndarray, t_b: int, extra: np.ndarray | None = None) -> np.ndarray:
    X, y = har_design(v, extra)
    ok = np.isfinite(X).all(axis=1) & np.isfinite(y)
    tr = np.where(ok & (np.arange(len(v)) < t_b))[0]
    beta, *_ = np.linalg.lstsq(X[tr], y[tr], rcond=None)
    resid = y[tr] - X[tr] @ beta
    smear = float(np.mean(np.exp(resid)))
    s = np.full(len(v), np.nan)
    pred_ok = np.isfinite(X).all(axis=1)
    s[pred_ok] = np.sqrt(np.exp(X[pred_ok] @ beta) * smear)
    s[:WARM] = np.nan
    return s


# ----------------------------------------------------------------------------- FHS
def fhs_quantiles(x: np.ndarray, sigma: np.ndarray, t: int, center: bool = True, window: int = Z_WINDOW, loc: float = 0.0) -> np.ndarray:
    lo = max(0, t - window)
    z = x[lo:t] / sigma[lo:t]
    z = z[np.isfinite(z)]
    q = np.quantile(z, GRID)
    if center:
        q = q - np.median(z)
    return loc + sigma[t] * q


@dataclass
class ScaleRun:
    quantiles: dict[str, np.ndarray]   # model -> [n_eval, len(GRID)]
    sigma: dict[str, np.ndarray]       # model -> [n_eval]
    notes: dict[str, int]


def run_scale_models(x: np.ndarray, v: np.ndarray, exog: np.ndarray | None, t_end: int | None = None,
                     models: tuple[str, ...] = ("S0", "S1", "S2", "S3", "S4", "S5", "S6"), center: bool = True) -> ScaleRun:
    """Walk-forward scale forecasts for target series x (zero-centred via median of z) for t in [MIN_HIST, t_end)."""
    n = len(x) if t_end is None else t_end
    ts = np.arange(MIN_HIST, n)
    out_q = {m: np.full((len(ts), len(GRID)), np.nan) for m in models}
    out_s = {m: np.full(len(ts), np.nan) for m in models}
    notes = {"garch_fail": 0, "gjr_fail": 0}
    s0, s1 = sigma_hist(x), sigma_ewma(x)
    prev_g = prev_j = None
    for b0 in range(MIN_HIST, n, REFIT):
        blk = np.arange(b0, min(b0 + REFIT, n))
        sig: dict[str, np.ndarray] = {}
        if "S0" in models:
            sig["S0"] = s0
        if "S1" in models:
            sig["S1"] = s1
        if {"S2", "S6"} & set(models):
            sig["S2"], prev_g, ok = sigma_garch_block(x[:n], b0, False, prev_g)
            notes["garch_fail"] += int(not ok)
        if "S3" in models:
            sig["S3"], prev_j, ok = sigma_garch_block(x[:n], b0, True, prev_j)
            notes["gjr_fail"] += int(not ok)
        if {"S4", "S6"} & set(models):
            sig["S4"] = sigma_har_block(v[:n], b0)
        if "S5" in models and exog is not None:
            sig["S5"] = sigma_har_block(v[:n], b0, exog[:n])
        if "S6" in models:
            sig["S6"] = np.sqrt(sig["S2"] * sig["S4"])
        for m in models:
            if m not in sig:
                continue
            for t in blk:
                out_s[m][t - MIN_HIST] = sig[m][t]
                out_q[m][t - MIN_HIST] = fhs_quantiles(x, sig[m], t, center=center)
    return ScaleRun(out_q, out_s, notes)


# ----------------------------------------------------------------------------- exogenous features for S5
def exog_matrix(bse_idx: pd.DataFrame, ix: pd.DataFrame, turnover_cr: pd.Series) -> np.ndarray:
    """Columns dated <= t-1 (shifted by one session): ln VIX, ln Nifty 5d RV, BSE log-turnover z(60d), |Nifty ret|."""
    ix = ix.reindex(bse_idx.index)
    nr = np.log(ix["nifty50_close"]).diff()
    f = pd.DataFrame(index=bse_idx.index)
    f["lnvix"] = np.log(ix["vix_close"])
    f["nifty_rv5"] = np.log((nr ** 2).rolling(5).sum().clip(lower=EPS))
    lt = np.log(turnover_cr.reindex(bse_idx.index).clip(lower=EPS))
    f["turn_z"] = (lt - lt.rolling(60).mean()) / lt.rolling(60).std()
    f["nifty_abs"] = nr.abs()
    f = f.shift(1)
    return f.values

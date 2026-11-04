"""Forecast-evaluation metrics and tests (implemented with numpy/scipy only; formulas stated in comments)."""
from __future__ import annotations

import numpy as np
from scipy import stats

from common import CENTRAL, GRID


def pinball(y: np.ndarray, q: np.ndarray) -> np.ndarray:
    """Per-observation mean pinball loss over GRID.  y:[n], q:[n,len(GRID)] -> [n]."""
    u = y[:, None] - q
    tau = GRID[None, :]
    return np.mean(np.maximum(tau * u, (tau - 1) * u), axis=1)


def coverage(y: np.ndarray, q: np.ndarray, level: float) -> tuple[float, np.ndarray]:
    lo_t, hi_t = CENTRAL[level]
    lo, hi = q[:, list(GRID).index(lo_t)], q[:, list(GRID).index(hi_t)]
    hit = ((y >= lo) & (y <= hi)).astype(int)
    return float(hit.mean()), hit


def kupiec(hit: np.ndarray, p: float) -> float:
    """Kupiec unconditional-coverage LR test p-value; p = nominal coverage."""
    n, x = len(hit), int(hit.sum())
    if n == 0:
        return np.nan
    ph = x / n
    def ll(pp):
        pp = min(max(pp, 1e-12), 1 - 1e-12)
        return x * np.log(pp) + (n - x) * np.log(1 - pp)
    lr = -2 * (ll(p) - ll(ph))
    return float(1 - stats.chi2.cdf(lr, 1))


def christoffersen_ind(hit: np.ndarray) -> float:
    """Christoffersen independence LR test p-value (first-order Markov on hit sequence)."""
    h = hit.astype(int)
    a, b = h[:-1], h[1:]
    n00 = int(((a == 0) & (b == 0)).sum()); n01 = int(((a == 0) & (b == 1)).sum())
    n10 = int(((a == 1) & (b == 0)).sum()); n11 = int(((a == 1) & (b == 1)).sum())
    if min(n00 + n01, n10 + n11) == 0:
        return np.nan
    pi01 = n01 / (n00 + n01); pi11 = n11 / (n10 + n11); pi = (n01 + n11) / (n00 + n01 + n10 + n11)
    def lg(p, k0, k1):
        p = min(max(p, 1e-12), 1 - 1e-12)
        return k0 * np.log(1 - p) + k1 * np.log(p)
    lr = -2 * (lg(pi, n00 + n10, n01 + n11) - lg(pi01, n00, n01) - lg(pi11, n10, n11))
    return float(1 - stats.chi2.cdf(lr, 1))


def _nw_var(d: np.ndarray, lag: int) -> float:
    d = d - d.mean()
    n = len(d)
    g0 = float(d @ d) / n
    s = g0
    for k in range(1, lag + 1):
        w = 1 - k / (lag + 1)
        s += 2 * w * float(d[k:] @ d[:-k]) / n
    return s / n


def diebold_mariano(loss_a: np.ndarray, loss_b: np.ndarray, lag: int = 5) -> tuple[float, float, float]:
    """H0: equal expected loss.  d = loss_b - loss_a  (positive => A better).  Returns (mean d, t-stat, one-sided p that A is better).
    Harvey-Leybourne-Newbold small-sample factor applied (h=1)."""
    d = np.asarray(loss_b) - np.asarray(loss_a)
    n = len(d)
    v = _nw_var(d, lag)
    if v <= 0:
        return float(d.mean()), np.nan, np.nan
    t = d.mean() / np.sqrt(v)
    hln = np.sqrt((n + 1 - 2 + (1 * (1 - 1)) / n) / n)  # h=1 -> sqrt((n-1)/n)
    t_adj = t * hln
    p = 1 - stats.t.cdf(t_adj, df=n - 1)
    return float(d.mean()), float(t_adj), float(p)


def qlike(var_hat: np.ndarray, proxy: np.ndarray) -> np.ndarray:
    r = proxy / var_hat
    return r - np.log(r) - 1


def oos_r2(y: np.ndarray, f: np.ndarray, f_bench: np.ndarray) -> float:
    """Campbell-Thompson out-of-sample R^2 of forecast f vs benchmark forecast f_bench."""
    return float(1 - np.sum((y - f) ** 2) / np.sum((y - f_bench) ** 2))


def clark_west(y: np.ndarray, f_alt: np.ndarray, f_nest: np.ndarray, lag: int = 0) -> tuple[float, float]:
    """Clark-West MSPE-adjusted test for nested models.  H1: alt (bigger) model has lower MSPE.  Returns (t, one-sided p)."""
    adj = (y - f_nest) ** 2 - ((y - f_alt) ** 2 - (f_nest - f_alt) ** 2)
    v = _nw_var(adj, lag) if lag else adj.var(ddof=1) / len(adj)
    t = adj.mean() / np.sqrt(v)
    return float(t), float(1 - stats.norm.cdf(t))


def binom_p(hits: int, n: int, p0: float) -> float:
    """One-sided exact binomial p-value for accuracy > p0."""
    return float(stats.binomtest(hits, n, p0, alternative="greater").pvalue)


def wilson(hits: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (np.nan, np.nan)
    p = hits / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (c - h, c + h)


def auc(y: np.ndarray, s: np.ndarray) -> float:
    r = stats.rankdata(s)
    n1 = int(y.sum()); n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return np.nan
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))

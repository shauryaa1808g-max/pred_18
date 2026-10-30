"""Self-tests of the forecasting machinery on synthetic data with known truth.  Run: python3 tests/test_pipeline.py"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import metrics as M  # noqa: E402
import models as P  # noqa: E402
from common import GRID  # noqa: E402


def sim_garch_t(n: int, seed: int, omega=2e-6, alpha=0.08, beta=0.90, nu=5.0):
    rng = np.random.default_rng(seed)
    h = omega / (1 - alpha - beta)
    x = np.empty(n)
    sig = np.empty(n)
    for t in range(n):
        sig[t] = np.sqrt(h)
        z = rng.standard_t(nu) * np.sqrt((nu - 2) / nu)
        x[t] = sig[t] * z
        h = omega + alpha * x[t] ** 2 + beta * h
    return x, sig


def test_metrics():
    rng = np.random.default_rng(0)
    # nominal coverage -> Kupiec p not tiny, independent hits -> Christoffersen p not tiny
    hit = (rng.random(4000) < 0.9).astype(int)
    assert M.kupiec(hit, 0.9) > 0.01
    assert M.christoffersen_ind(hit) > 0.01
    # clearly wrong coverage -> rejected
    assert M.kupiec((rng.random(4000) < 0.8).astype(int), 0.9) < 1e-6
    # DM: identical losses -> d=0
    l = rng.random(500)
    d, t, p = M.diebold_mariano(l, l)
    assert d == 0 or np.isnan(t)
    # DM: A strictly better -> small p
    d, t, p = M.diebold_mariano(l, l + 0.1 + 0.01 * rng.standard_normal(500))
    assert p < 1e-6
    # pinball of true quantiles is lower than that of shifted quantiles
    y = rng.standard_normal(20000)
    from scipy.stats import norm
    q_true = np.tile(norm.ppf(GRID), (len(y), 1))
    assert M.pinball(y, q_true).mean() < M.pinball(y, q_true + 0.5).mean()
    # Clark-West: noise predictor should not be significant
    yy = rng.standard_normal(2000); f_nest = np.zeros(2000); f_alt = 0.05 * rng.standard_normal(2000)
    assert M.clark_west(yy, f_alt, f_nest)[1] > 0.01
    # wilson / binom sanity
    lo, hi = M.wilson(55, 100); assert lo < 0.55 < hi
    assert 0.1 < M.binom_p(55, 100, 0.5) < 0.2
    print("metrics tests ok")


def test_models_recover_vol():
    x, true_sig = sim_garch_t(2600, seed=1)
    v = np.clip(x ** 2, 1e-8, None)
    run = P.run_scale_models(x, v, None, models=("S0", "S1", "S2", "S4"))
    y = x[P.MIN_HIST:]
    pl = {m: M.pinball(y, run.quantiles[m]).mean() for m in run.quantiles}
    print("synthetic pinball:", {k: round(v_ * 1e3, 4) for k, v_ in pl.items()})
    # oracle for reference
    from scipy.stats import t as tdist
    nu = 5.0
    zq = tdist.ppf(GRID, nu) * np.sqrt((nu - 2) / nu)
    q_or = true_sig[P.MIN_HIST:, None] * zq[None, :]
    pl_or = M.pinball(y, q_or).mean()
    print("oracle pinball:", round(pl_or * 1e3, 4))
    assert pl["S2"] < pl["S0"], "GARCH should beat untimed benchmark on GARCH data"
    assert pl["S1"] < pl["S0"]
    assert pl_or <= pl["S2"] * 1.001
    # coverage near nominal for S2
    for lev in (0.5, 0.8, 0.9, 0.95):
        c, hit = M.coverage(y, run.quantiles["S2"], lev)
        assert abs(c - lev) < 0.04, (lev, c)
    # no NaNs in forecasts
    for m in run.quantiles:
        assert np.isfinite(run.quantiles[m]).all(), m
    print("recover-vol tests ok; notes", run.notes)


def test_no_lookahead():
    x, _ = sim_garch_t(1900, seed=2)
    v = np.clip(x ** 2, 1e-8, None)
    full = P.run_scale_models(x, v, None, models=("S0", "S1", "S2", "S3", "S4", "S6"))
    cut = 1500
    trunc = P.run_scale_models(x[:cut], v[:cut], None, models=("S0", "S1", "S2", "S3", "S4", "S6"))
    n_t = cut - P.MIN_HIST
    # (a) truncation invariance: forecasts for t < cut must be identical when later data are removed
    # (block boundaries align because both runs start at MIN_HIST with the same REFIT)
    last_full_block_end = P.MIN_HIST + (n_t // P.REFIT) * P.REFIT
    n_cmp = last_full_block_end - P.MIN_HIST
    for m in trunc.quantiles:
        a, b = trunc.quantiles[m][:n_cmp], full.quantiles[m][:n_cmp]
        assert np.allclose(a, b, rtol=1e-9, atol=1e-12, equal_nan=True), f"lookahead in {m}"
    # (b) future-scramble invariance
    x2 = x.copy(); rng = np.random.default_rng(9); x2[cut:] = rng.standard_normal(len(x) - cut) * 0.05
    v2 = np.clip(x2 ** 2, 1e-8, None)
    scr = P.run_scale_models(x2, v2, None, models=("S0", "S1", "S2", "S3", "S4", "S6"))
    for m in trunc.quantiles:
        assert np.allclose(scr.quantiles[m][:n_cmp], full.quantiles[m][:n_cmp], rtol=1e-9, atol=1e-12, equal_nan=True), f"lookahead(scramble) in {m}"
    print(f"no-lookahead tests ok on {n_cmp} forecast dates x {len(trunc.quantiles)} models")


if __name__ == "__main__":
    test_metrics()
    test_models_recover_vol()
    test_no_lookahead()
    print("ALL TESTS PASSED")

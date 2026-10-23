"""Runner for tests/test_same_row_real.py.  Usage: python3 _same_row_runner.py <row_index> <variant A|B> <workdir> [inject]
Builds a working copy of data/processed truncated at row t (data up to t-1 real; row t replaced by garbage variant A or B),
then returns every forecast for row t (scale models for R/G/I, range models, location features, ridge and logit)."""
import os, pickle, shutil, sys
from pathlib import Path
import numpy as np, pandas as pd
repo = Path(__file__).resolve().parents[1]
i0, variant, work = int(sys.argv[1]), sys.argv[2], Path(sys.argv[3]); inject = len(sys.argv) > 4 and sys.argv[4] == "inject"
sys.path.insert(0, str(repo / "src"))
SRC = repo / "data" / "processed"
shutil.rmtree(work, ignore_errors=True); (work / "data" / "processed").mkdir(parents=True)
shutil.copy(repo / "data" / "corp_actions_verified.csv", work / "data" / "corp_actions_verified.csv") if (repo / "data" / "corp_actions_verified.csv").exists() else None
b = pd.read_csv(SRC / "bse_daily.csv", parse_dates=["date"]); dt0 = b.date.iloc[i0]
mult = {"A": (1.3, 1.2, 0.5), "B": (0.7, 0.8, 1.5)}[variant]
for f in ("bse_daily.csv", "index_daily.csv", "breadth_daily.csv"):
    df = pd.read_csv(SRC / f, parse_dates=["date"]); df = df[df.date <= dt0].copy(); last = df.date == dt0
    if f == "bse_daily.csv":
        cols = ["open", "high", "low", "close"]; df.loc[last, cols] = df.loc[last, cols].values * mult[0]; df.loc[last, "turnover_cr"] *= 5 * mult[2]; df["vol"] = df["vol"].astype(float); df.loc[last, "vol"] *= 3 * mult[2]
    elif f == "index_daily.csv":
        num = [c for c in df.columns if c != "date" and "volume" not in c]; df.loc[last, num] = df.loc[last, num].values * mult[1]
    else:
        df.loc[last, ["adv_share", "dec_share"]] = [min(0.95, 0.5 * mult[2] + 0.1), 0.2]; df.loc[last, "med_ret"] = 0.03 * (mult[2] - 1)
    df.to_csv(work / "data" / "processed" / f, index=False)
os.chdir(work)
import models as P
if inject:      # positive control: the realised target leaks into the filtered-historical-simulation window
    def leaky(x, sigma, t, center=True, window=P.Z_WINDOW, loc=0.0):
        lo = max(0, t - window); z = x[lo:t + 1] / sigma[lo:t + 1]; z = z[np.isfinite(z)]
        q = np.quantile(z, P.GRID); q = q - np.median(z) if center else q
        return loc + sigma[t] * q
    P.fhs_quantiles = leaky
import walkforward as W, location as L, run_location as RL
d, t, ix, exog = W.build()
runs = W.run_targets(t, exog, None)
out = {(n, m): q[-1] for n, r in runs.items() for m, q in r.quantiles.items()}
out.update({("rho", k): q[-1] for k, q in W.run_range(t, None).items()})
d, t, F, s, R, y_std, y_dir = RL.prep()
mu = L.walk(F, y_std, y_dir, RL.ALL_COLS, alpha=1000, C=None, kind="ridge"); p = L.walk(F, y_std, y_dir, RL.ALL_COLS, alpha=0, C=0.01, kind="logit")
out[("loc", "mu")] = np.array([mu[-1]]); out[("loc", "p")] = np.array([p[-1]]); out[("loc", "s")] = np.array([s[-1]])
for c in F.columns: out[("feat", c)] = np.array([F[c].iloc[-1]])
pickle.dump(out, open(work.parent / f"{work.name}.pkl", "wb")); print("ok", len(d))

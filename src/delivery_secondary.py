"""SECONDARY (non-gating): does delivery % (info <= t-1) predict next-session return, |return| or direction?  Plus a weekday-scale check."""
import numpy as np, pandas as pd
from scipy import stats
import metrics as M, models as P
from common import load_bse, targets, EPS
d = load_bse(); t = targets(d)
s = pd.Series(P.sigma_ewma(t["R"].values), index=d.index)
dv = d["deliv_pct"]
z = ((dv - dv.rolling(60).mean()) / dv.rolling(60).std()).shift(1)       # delivery z-score known at t-1
frame = pd.DataFrame({"R": t["R"], "absz": t["R"].abs() / s, "z": z, "up": (t["R"] > 0).astype(int), "r1": t["R"].shift(1)}).dropna()
frame = frame.loc["2020-06-01":]                                           # delivery series complete + 60d warm-up
def hac_t(y, x, lag=5):
    X = np.column_stack([np.ones(len(x)), x]); b = np.linalg.lstsq(X, y, rcond=None)[0]; e = y - X @ b
    n = len(y); Xe = X * e[:, None]; S = Xe.T @ Xe / n
    for k in range(1, lag + 1):
        G = Xe[k:].T @ Xe[:-k] / n; S += (1 - k / (lag + 1)) * (G + G.T)
    XtXi = np.linalg.inv(X.T @ X / n); V = XtXi @ S @ XtXi / n
    return b[1], b[1] / np.sqrt(V[1, 1])
for lab, f in (("2020-06..2026-10", frame), ("Dev 2020-06..2024-06", frame.loc[:"2024-06-28"]), ("Val+Final 2024-07+", frame.loc["2024-07-01":])):
    b1, t1 = hac_t(f["R"].values, f["z"].values); b2, t2 = hac_t(f["absz"].values, f["z"].values)
    b3, t3 = hac_t(f["R"].values, (f["z"] * np.sign(f["r1"])).values)
    print(f"{lab:24s} n={len(f):4d} | R~z: b={b1:+.5f} t={t1:+.2f} | |R|/sigma~z: b={b2:+.4f} t={t2:+.2f} | R~z*sign(r1): b={b3:+.5f} t={t3:+.2f}")
# walk-forward OOS for the R ~ z regression (expanding OLS, start 2022)
ys, ps = [], []
idx = frame.index
for i in range(400, len(frame)):
    tr = frame.iloc[:i]; X = np.column_stack([np.ones(len(tr)), tr["z"]]); b = np.linalg.lstsq(X, tr["R"].values, rcond=None)[0]
    ps.append(b[0] + b[1] * frame["z"].iloc[i]); ys.append(frame["R"].iloc[i])
ys, ps = np.array(ys), np.array(ps); bench = np.array([frame["R"].iloc[:i].mean() for i in range(400, len(frame))])
print("walk-forward OOS R2 vs expanding mean:", round(M.oos_r2(ys, ps, bench), 4), " Clark-West p:", round(M.clark_west(ys, ps, bench)[1], 3), " n=", len(ys))
# weekday scale check: mean of (R/sigma)^2 by weekday, Final window
f = pd.DataFrame({"z2": (t["R"] / s) ** 2, "dow": d.index.dayofweek}).dropna()
for lab, g in (("all", f), ("Val+Final", f.loc["2024-07-01":]), ("last250", f.iloc[-250:])):
    m = g.groupby("dow").z2.mean().round(2).to_dict(); n = g.groupby("dow").size().to_dict()
    print(f"mean (R/sigma)^2 by weekday [{lab}] (0=Mon): {m}   n={n}")

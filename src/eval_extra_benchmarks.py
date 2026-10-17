"""Extra untimed benchmarks for the close-to-close target (audit finding F2):
  EMP250 / EMP500 : trailing-N median-centred empirical return quantiles (an adaptive but untimed benchmark)
  S0xc            : the pre-registered S0 scaled by ONE constant c fitted ex-post on the evaluation window itself (an optimistic upper bound for 'level adaptation only')
Compared with S1, S4, S6 via DM on pinball loss (Newey-West 5 lags, HLN)."""
import numpy as np, pandas as pd
import metrics as M, models as P
from common import GRID, load_bse, targets
d = load_bse(); t = targets(d); R = t["R"].values
fc = pd.read_csv("results/forecasts_R.csv", parse_dates=["date"])
piv = {m: g.set_index("date")[[f"q{g:g}" for g in GRID]] for m, g in fc.groupby("model")}
dates = piv["S0"].index; y = fc[fc.model == "S0"].set_index("date")["y"].values
idx0 = P.MIN_HIST
def emp(N):
    out = np.full((len(dates), len(GRID)), np.nan)
    for i, tt in enumerate(range(idx0, idx0 + len(dates))):
        w = R[max(0, tt - N):tt]; q = np.quantile(w, GRID); out[i] = q - np.median(w)
    return out
bench = {"EMP250": emp(250), "EMP500": emp(500)}
wins = {"dev": (None, "2024-06-28"), "val": ("2024-07-01", "2025-06-30"), "final": ("2025-07-01", None), "devval": (None, "2025-06-30"), "valfinal": ("2024-07-01", None)}
rows = []
for w, (lo, hi) in wins.items():
    m = np.ones(len(dates), bool)
    if lo: m &= dates >= pd.Timestamp(lo)
    if hi: m &= dates <= pd.Timestamp(hi)
    yy = y[m]
    q0 = piv["S0"].values[m]
    # ex-post optimal constant for S0 on this very window (grid search over c)
    best = min(((M.pinball(yy, q0 * c).mean(), c) for c in np.linspace(0.4, 1.4, 101)))
    b = dict(bench); b["S0xc(ex-post c=%.2f)" % best[1]] = q0 * best[1]
    for bn, bq in b.items():
        bq = bq[m] if bq.shape[0] == len(dates) else bq
        plb = M.pinball(yy, bq)
        cov90 = M.coverage(yy, bq, 0.9)[0]
        for mn in ("S1", "S4", "S6"):
            plm = M.pinball(yy, piv[mn].values[m])
            dm, tt_, p = M.diebold_mariano(plm, plb)
            rows.append({"window": w, "n": int(m.sum()), "benchmark": bn, "bench_pinball_x1e4": 1e4 * plb.mean(), "bench_cov90": cov90, "model": mn, "model_pinball_x1e4": 1e4 * plm.mean(), "gain_x1e4": 1e4 * dm, "dm_p_model_better": p})
df = pd.DataFrame(rows); df.to_csv("results/eval_extra_benchmarks.csv", index=False)
pd.set_option("display.width", 220)
print(df[df.model == "S6"].round(4).to_string(index=False))
print(); print(df[(df.window == "final")].round(4).to_string(index=False))

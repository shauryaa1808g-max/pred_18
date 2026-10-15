"""Exploratory (NOT pre-registered) walk-forward check: how often is the next close's / open-to-close direction called right, and what is the typical miss?
Features known before the open: previous US session S&P 500 return (FRED), yesterday's open-to-close and close-to-close returns, and (for open-to-close) the actual open gap.
Expanding-window OLS, minimum 500 sessions, past data only.  Run from the repo root:  python3 src/direction_check.py
Written after the lead saw the first numbers (2026-10-15); treat as descriptive, not a validated claim."""
import numpy as np, pandas as pd
from scipy import stats
from common import load_bse, targets
d = load_bse(); t = targets(d)
sp = pd.read_csv('data/raw/macro/SP500.csv'); sp.columns = ['date', 'v']; sp['v'] = pd.to_numeric(sp['v'], errors='coerce'); sp = sp.dropna(); sp['date'] = pd.to_datetime(sp['date']); sp = sp.set_index('date').v
spr = np.log(sp).diff().dropna(); idx = spr.index
X = pd.Series({k: (spr.iloc[idx.searchsorted(k) - 1] if idx.searchsorted(k) > 0 else np.nan) for k in d.index})   # latest US return dated strictly before the Indian session
df = pd.DataFrame({'G': t['G'], 'I': t['I'], 'R': t['R'], 'sp': X, 'pI': t['I'].shift(1), 'pR': t['R'].shift(1)}).dropna()
LV, COST = 3400.0, 0.0010
def wf(cols, y, n0=500):
    Xm, Y = df[cols].values, df[y].values
    return pd.Series([np.r_[1, Xm[i]] @ np.linalg.lstsq(np.c_[np.ones(i), Xm[:i]], Y[:i], rcond=None)[0] for i in range(n0, len(df))], index=df.index[n0:])
def report(lab, p, a):
    nz = a != 0; hit = (np.sign(p) == np.sign(a))[nz]
    pv = stats.binomtest(int(hit.sum()), int(nz.sum()), 0.5, alternative='greater').pvalue
    yr = pd.DataFrame({'h': hit.values, 'y': a[nz].index.year}).groupby('y').h.mean()
    print(f"{lab}: direction right {100*hit.mean():.1f}% (n={nz.sum()}, p={pv:.4f}); by year " + ' '.join(f'{y}:{100*v:.0f}%' for y, v in yr.items()))
    print(f"   typical miss: model Rs {np.mean(np.abs(a-p))*LV:.0f} vs 'unchanged' Rs {np.mean(np.abs(a))*LV:.0f} (at Rs {LV:.0f})")
pR = wf(['sp', 'pI', 'pR'], 'R'); report('Close-to-close R from evening-before information', pR, df.R.loc[pR.index])
pO = wf(['sp', 'pI', 'pR'], 'G'); report('Opening gap G from evening-before information', pO, df.G.loc[pO.index])
pI = wf(['G', 'sp', 'pI', 'pR'], 'I'); aI = df.I.loc[pI.index]; report('Open-to-close I given the actual open', pI, aI)
net = np.exp(np.sign(pI) * aI) - 1 - COST
print(f"Trade open->close in the predicted direction, every day: mean net {100*net.mean():+.3f}% per trade, win {100*(net>0).mean():.0f}%, t={net.mean()/(net.std()/np.sqrt(len(net))):+.1f}; last 250: {100*net.iloc[-250:].mean():+.3f}%")

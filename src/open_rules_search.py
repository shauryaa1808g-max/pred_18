"""Exploratory search for a buy / short / stay-out rule at the 09:15 open (NOT pre-registered; read the result as descriptive).
Every rule: at the open, if a feature known by 09:15 is unusually large (|z| > 1, z = feature / its own EXPANDING past std), go long or short for open->close; costs 0.10% round trip.
Family fixed before looking: 9 features x {follow, fade} = 18 rules.  Periods: Dev 2019-02..2024-06, Val+Final 2024-07..2026-10-12.  Holm correction over the 18 rules.
Run from the repo root: python3 src/open_rules_search.py"""
import numpy as np, pandas as pd
from scipy import stats
from common import load_bse, targets, load_index, index_returns
d = load_bse(); t = targets(d)
sp = pd.read_csv('data/raw/macro/SP500.csv'); sp.columns = ['date', 'v']; sp['v'] = pd.to_numeric(sp['v'], errors='coerce'); sp = sp.dropna(); sp['date'] = pd.to_datetime(sp['date']); sp = sp.set_index('date').v
spr = np.log(sp).diff().dropna(); idx = spr.index
SP = pd.Series({k: (spr.iloc[idx.searchsorted(k) - 1] if idx.searchsorted(k) > 0 else np.nan) for k in d.index})
try:
    ir = index_returns(load_index()); nif = ir['nifty50'].shift(1).reindex(d.index) if 'nifty50' in ir else None
except Exception as e:
    nif = None
adjc = d['close'] / np.concatenate([np.cumprod(d['ca_factor'].fillna(1.0).values[::-1])[::-1][1:], [1.0]])
F = pd.DataFrame({'gap': t['G'], 'sp_prior_us': SP, 'yday_intraday': t['I'].shift(1), 'yday_return': t['R'].shift(1),
                  'ret_5d': np.log(adjc / adjc.shift(5)).shift(1), 'ret_20d': np.log(adjc / adjc.shift(20)).shift(1),
                  'yday_volume_x': (d['vol'] / d['vol'].rolling(20).mean()).shift(1) - 1,
                  'brk20_high': (adjc.shift(1) / adjc.shift(2).rolling(20).max() - 1)})
if nif is not None: F['nifty_prior'] = nif
F['I'] = t['I']
F = F.dropna()
COST = 0.0010
rows = []
for c in [c for c in F.columns if c != 'I']:
    x = F[c]; z = x / x.expanding(250).std().shift(1)          # past-only scale
    for mode, sgn in (('follow', 1), ('fade', -1)):
        m = (z.abs() > 1)
        r = (sgn * np.sign(z[m]) * F['I'][m]); net = np.exp(r) - 1 - COST
        for per, sl in (('Dev', slice(None, '2024-06-30')), ('ValFinal', slice('2024-07-01', None))):
            n = net.loc[sl]
            rows.append({'feature': c, 'mode': mode, 'period': per, 'trades': len(n), 'mean_net_pct': 100 * n.mean(), 'win_pct': 100 * (n > 0).mean(), 't': n.mean() / (n.std(ddof=1) / np.sqrt(len(n))) if len(n) > 2 else np.nan})
R = pd.DataFrame(rows)
dev = R[R.period == 'Dev'].set_index(['feature', 'mode']); vf = R[R.period == 'ValFinal'].set_index(['feature', 'mode'])
out = dev[['trades', 'mean_net_pct', 't']].join(vf[['trades', 'mean_net_pct', 't']], lsuffix='_dev', rsuffix='_vf')
p = 2 * stats.norm.sf(out.t_vf.abs()); order = np.argsort(p); holm = np.empty(len(p)); run = 0
for rank, i in enumerate(order): run = max(run, min(1, p[i] * (len(p) - rank))); holm[i] = run
out['p_vf'] = p; out['holm_vf'] = holm
pd.set_option('display.width', 200); pd.set_option('display.float_format', lambda v: f'{v:8.3f}')
print(out.sort_values('t_vf', ascending=False).to_string())
print('\nRules with positive mean net AND t>2 in BOTH periods:'); print(out[(out.mean_net_pct_dev > 0) & (out.mean_net_pct_vf > 0) & (out.t_dev > 2) & (out.t_vf > 2)].to_string())
out.sort_values('t_vf', ascending=False).to_csv('results/open_rules_search.csv')

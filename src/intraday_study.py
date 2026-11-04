"""Exploratory intraday study (NOT pre-registered): does anything known at 10:15 IST (after the first hour) predict where BSE ends the day?
Data: Yahoo hourly bars, 2 years (about 500 sessions), BSE.NS, ^NSEI and peers CDSL/MCX/ANGELONE; hourly bars start 09:15, 10:15, ... 15:15 (the last is a 15-minute bar).
Price at 10:15 = close of the 09:15 bar; 'close' = close of the last bar (last traded price, not exactly the official auction close before 3 Aug 2026).
Run from the repo root after saving the Yahoo files (see the fetch loop in the session log):  python3 src/intraday_study.py <dir with h60_*.json>"""
import sys, json, glob
import numpy as np, pandas as pd
from scipy import stats
D = sys.argv[1]
def load(sym):
    r = json.load(open(f"{D}/h60_{sym}.json"))["chart"]["result"][0]; q = r["indicators"]["quote"][0]
    df = pd.DataFrame({"t": pd.to_datetime(r["timestamp"], unit="s", utc=True).tz_convert("Asia/Kolkata"), "o": q["open"], "h": q["high"], "l": q["low"], "c": q["close"], "v": q["volume"]}).dropna(subset=["c"])
    df["date"] = df.t.dt.strftime("%Y-%m-%d"); df["slot"] = ((df.t.dt.hour * 60 + df.t.dt.minute - 555) // 60).astype(int)
    return df
def sessions(sym):
    df = load(sym); out = {}
    for d, g in df.groupby("date"):
        if len(g) < 6: continue
        g = g.sort_values("t"); out[d] = {"open": float(g.o.iloc[0]), "p1": float(g.c.iloc[0]), "close": float(g.c.iloc[-1]), "v1": float(g.v.iloc[0]), "n": len(g)}
    return pd.DataFrame(out).T.astype(float)
B = sessions("BSE.NS"); N = sessions("%5ENSEI"); P = {k: sessions(k + ".NS") for k in ("CDSL", "MCX", "ANGELONE")}
idx = B.index.intersection(N.index)
df = pd.DataFrame(index=idx)
df["prev_close"] = B.close.shift(1).reindex(idx); df["gap"] = np.log(B.open / df.prev_close)
df["r1"] = np.log(B.p1 / B.open).reindex(idx); df["Y"] = np.log(B.close / B.p1).reindex(idx)
df["n_r1"] = np.log(N.p1 / N.open).reindex(idx); df["n_gap"] = np.log(N.open / N.close.shift(1)).reindex(idx)
pr = pd.concat([np.log(P[k].p1 / P[k].open) for k in P], axis=1); df["peer_r1"] = pr.mean(axis=1).reindex(idx)
df["rel1"] = df.r1 - df.n_r1                      # (Yahoo hourly volume is zero on most sessions, so no volume feature)
df["prevR"] = np.log(B.close / B.close.shift(1)).shift(1).reindex(idx)
df = df.replace([np.inf, -np.inf], np.nan).dropna(); df = df[(df.index >= "2024-10-17")]
print(f"{len(df)} sessions {df.index[0]} .. {df.index[-1]};  price at 10:15 to close: std {100*df.Y.std():.2f}%, mean |Y| Rs {np.mean(np.abs(df.Y))*3400:.1f} (at Rs 3,400)")
LV = 3400.0; COST = 0.0010
# ---- Q1: walk-forward linear prediction of Y from info at 10:15
feats = {"first hour return": ["r1"], "gap": ["gap"], "Nifty first hour": ["n_r1"], "peers first hour": ["peer_r1"], "BSE minus Nifty": ["rel1"], "all of them": ["r1", "gap", "n_r1", "n_gap", "peer_r1", "prevR"]}
def wf(cols, n0=150):
    X = df[cols].values; y = df.Y.values; out = []
    for i in range(n0, len(df)):
        b = np.linalg.lstsq(np.c_[np.ones(i), X[:i]], y[:i], rcond=None)[0]; out.append(np.r_[1, X[i]] @ b)
    return np.array(out)
a = df.Y.values[150:]; mean_hist = np.array([df.Y.values[:i].mean() for i in range(150, len(df))])
print(f"\nQ1  predict the move from 10:15 to the close (walk-forward, n={len(a)}):  baseline 'price stays' typical miss Rs {np.mean(np.abs(a))*LV:.1f}")
for name, cols in feats.items():
    p = wf(cols); sse, sse0 = np.sum((a - p) ** 2), np.sum((a - mean_hist) ** 2)
    hit = (np.sign(p) == np.sign(a)).mean()
    print(f"   {name:20s} OOS R2 vs mean {100*(1-sse/sse0):+5.2f}%   typical miss Rs {np.mean(np.abs(a-p))*LV:5.1f}   direction right {100*hit:.1f}%   (last 150: miss Rs {np.mean(np.abs(a-p)[-150:])*LV:.1f} vs {np.mean(np.abs(a)[-150:])*LV:.1f})")
# ---- Q2: rules at 10:15 (enter at the 10:15 price, exit at the close), simple returns, 0.10% cost, Dev = first 60%, Val = last 40%
rows = []
cut = int(len(df) * 0.6)
for c in ["r1", "gap", "n_r1", "peer_r1", "rel1"]:
    z = df[c] / df[c].expanding(60).std().shift(1)
    for mode, sg in (("follow", 1), ("fade", -1)):
        m = z.abs() > 1; side = sg * np.sign(z[m]); net = side * (np.exp(df.Y[m]) - 1) - COST
        for per, sl in (("Dev", slice(None, df.index[cut - 1])), ("Val", slice(df.index[cut], None))):
            n = net.loc[sl]; rows.append((c, mode, per, len(n), 100 * n.mean(), (n.mean() / (n.std(ddof=1) / np.sqrt(len(n)))) if len(n) > 2 else np.nan))
R = pd.DataFrame(rows, columns=["feature", "mode", "period", "trades", "mean_net_pct", "t"]).pivot_table(index=["feature", "mode"], columns="period", values=["trades", "mean_net_pct", "t"])
print("\nQ2  trade rules at 10:15 (enter at the 10:15 price, exit at the close, 0.10% cost; |signal|>1 sd):")
print(R.round(2).to_string())
both = R[(R[("mean_net_pct", "Dev")] > 0) & (R[("mean_net_pct", "Val")] > 0) & (R[("t", "Dev")] > 2) & (R[("t", "Val")] > 2)]
print("\nrules positive with t>2 in BOTH periods:", "none" if both.empty else both)

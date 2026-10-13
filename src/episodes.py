"""Episode study with selection rules fixed in docs/PREREGISTRATION.md section 5 (E1-E5).  Descriptive only; no forecasting claims.

E1 Nifty 50 close-to-close <= -2.5%             E2 India VIX close >= 25 (merge gaps <= 5 sessions)
E3 Nifty 50 >= 10% below trailing-250d closing high   E4 |R_BSE| >= 8% or idiosyncratic |R - beta*Nifty| >= 3 x trailing-60d resid SD
E5 BSE Ltd results announcement dates (supplied in data/results_dates.csv from the company-record dossier)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from common import EPS, index_returns, load_bse, load_index, targets

RES = Path("results")


def boot_ci(x: np.ndarray, stat=np.median, n: int = 4000, seed: int = 0) -> tuple[float, float]:
    x = x[np.isfinite(x)]
    if len(x) < 3:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    s = [stat(rng.choice(x, len(x))) for _ in range(n)]
    return tuple(np.percentile(s, [5, 95]))


def event_metrics(d, t, ir, days: list[pd.Timestamp], label: str) -> pd.DataFrame:
    idx = d.index
    R = t["R"]
    nifty = ir["r_nifty50"]
    cap = ir["r_capmkts"] if "r_capmkts" in ir else pd.Series(np.nan, index=idx)
    # trailing 60d daily vol of BSE returns known before the event
    vol60 = R.rolling(60).std().shift(1)
    tov = d["turnover_cr"]
    tov60 = tov.rolling(60).mean().shift(1)
    rows = []
    for day in days:
        if day not in idx:
            continue
        i = idx.get_loc(day)
        if i < 130 or i + 20 >= len(idx):
            # keep the event but mark forward windows unavailable
            pass
        # beta from the 120 sessions before the event
        lo = max(0, i - 120)
        xs, ys = nifty.values[lo:i], R.values[lo:i]
        m = np.isfinite(xs) & np.isfinite(ys)
        beta = np.cov(xs[m], ys[m])[0, 1] / np.var(xs[m], ddof=1) if m.sum() > 60 else np.nan
        r0 = R.iloc[i]
        pre_close = d["prev"].iloc[i]
        rec = None
        for k in range(1, 61):
            if i + k >= len(idx):
                break
            if d["close"].iloc[i + k] >= pre_close:
                rec = k
                break
        fwd = lambda k: float(np.log(d["close"].iloc[i + k] / d["close"].iloc[i])) if i + k < len(idx) else np.nan  # noqa: E731
        rows.append({
            "set": label, "date": day.date(), "R": r0, "nifty_R": nifty.iloc[i],
            "excess_vs_nifty": r0 - nifty.iloc[i], "excess_beta_adj": r0 - beta * nifty.iloc[i] if np.isfinite(beta) else np.nan,
            "excess_vs_capmkts": r0 - cap.iloc[i] if np.isfinite(cap.iloc[i]) else np.nan,
            "next_R": R.iloc[i + 1] if i + 1 < len(idx) else np.nan,
            "next_absR_over_vol60": abs(R.iloc[i + 1]) / vol60.iloc[i + 1] if i + 1 < len(idx) and np.isfinite(vol60.iloc[i + 1]) else np.nan,
            "cum5": fwd(5), "cum20": fwd(20),
            "turnover_x": tov.iloc[i] / tov60.iloc[i] if np.isfinite(tov60.iloc[i]) else np.nan,
            "recover_sessions": rec if r0 < 0 else np.nan,
        })
    return pd.DataFrame(rows)


def merge_runs(days: list[pd.Timestamp], idx: pd.DatetimeIndex, gap: int = 5) -> list[pd.Timestamp]:
    """Collapse consecutive flagged sessions (gap <= `gap`) into one episode; return first day of each."""
    out, last = [], None
    for dday in days:
        i = idx.get_loc(dday)
        if last is None or i - last > gap:
            out.append(dday)
        last = i
    return out


def main():
    RES.mkdir(exist_ok=True)
    d = load_bse(); t = targets(d); ix = load_index().reindex(d.index)
    ir = index_returns(ix)
    nifty = ir["r_nifty50"]
    R = t["R"]
    idx = d.index
    sets: dict[str, list[pd.Timestamp]] = {}
    sets["E1_nifty_le_-2.5pct"] = list(idx[(nifty <= -0.025).fillna(False).values])
    vix = ix["vix_close"]
    sets["E2_vix_ge_25_episode_start"] = merge_runs(list(idx[(vix >= 25).fillna(False).values]), idx)
    lvl = ix["nifty50_close"]
    dd = lvl / lvl.rolling(250, min_periods=120).max() - 1
    sets["E3_nifty_dd_ge_10pct_episode_start"] = merge_runs(list(idx[(dd <= -0.10).fillna(False).values]), idx)
    big = (R.abs() >= 0.08)
    beta = (R.rolling(120).cov(nifty) / nifty.rolling(120).var()).shift(1)
    resid = R - beta * nifty
    rsd = resid.rolling(60).std().shift(1)
    idio = (resid.abs() >= 3 * rsd)
    sets["E4a_BSE_abs_ret_ge_8pct"] = list(idx[big.fillna(False).values])
    sets["E4b_BSE_idiosyncratic_3sd"] = list(idx[idio.fillna(False).values])
    rd = Path("data/results_dates.csv")
    if rd.exists():
        rdf = pd.read_csv(rd, parse_dates=["first_tradable_session"])
        sets["E5_results_reaction_session"] = [x for x in rdf["first_tradable_session"] if x in idx]
    allrows = []
    for k, days in sets.items():
        allrows.append(event_metrics(d, t, ir, days, k))
    ev = pd.concat(allrows, ignore_index=True)
    ev.to_csv(RES / "episodes_events.csv", index=False)
    summ = []
    for k, g in ev.groupby("set"):
        row = {"set": k, "n": len(g)}
        for c in ["R", "excess_beta_adj", "excess_vs_capmkts", "next_R", "next_absR_over_vol60", "cum5", "cum20", "turnover_x", "recover_sessions"]:
            x = g[c].values.astype(float)
            lo, hi = boot_ci(x)
            row[f"{c}_med"] = np.nanmedian(x) if np.isfinite(x).any() else np.nan
            row[f"{c}_ci90"] = f"[{lo:.4f},{hi:.4f}]"
            row[f"{c}_n"] = int(np.isfinite(x).sum())
        row["share_next_up"] = float((g["next_R"] > 0).mean())
        summ.append(row)
    pd.DataFrame(summ).to_csv(RES / "episodes_summary.csv", index=False)
    print(pd.DataFrame(summ)[["set", "n", "R_med", "excess_beta_adj_med", "next_R_med", "next_absR_over_vol60_med", "cum20_med", "share_next_up"]].to_string())


if __name__ == "__main__":
    main()

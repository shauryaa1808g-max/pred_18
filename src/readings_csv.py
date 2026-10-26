"""Every reading given to the user, stored in CSV files (rebuilt from the logs each time, so the files can never drift from what was shown).

  python3 src/readings_csv.py          # rebuild results/readings/readings.csv (all days, one row per reading) and results/readings/by_day/<date>.csv

Kinds of row (column `kind`):
  open_range                the 08:30 scoreboard entry: open range and open pin-point (= previous close), plus the close range for the day
  nse_preopen               one NSE pre-open snapshot (indicative or FINAL price, orders waiting), as read by the 09:00 / 09:09 jobs
  day_high_low_pre_open     day-ahead high / low pin-points (median) and bands of the day (src/hl_model.py, results/hl_dayahead_<date>.json)
  day_high_low_after_open   the same once the official open is known (results/hl_dayahead_<date>_open<price>.json)
  table                     one row of the hour-by-hour table exactly as logged (results/hourly_table_log.jsonl); `printed_row` is the row as printed
Scoring columns are filled in as the facts arrive: `window_actual_*` / `window_*_error_rs` / `window_*_in50|in90` once the row's own window is over (hourly rows: Yahoo 1-minute high / low from
results/hourly_table_scored.csv; whole-day rows: the OFFICIAL high / low), `official_*` and the `*_error_rs` / `*_in50|in90` of the open and the close once NSE's official bar is in the repo (about 16:35 IST).
Errors are actual minus predicted.  A blank cell means "not applicable" or "not known yet"; nothing is ever filled in from a recomputed prediction.
"""
from __future__ import annotations

import datetime as dt
import glob
import json
import math
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

OUT = Path("results/readings")
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
COLS = ["date", "time_ist", "kind", "source", "price_now",
        "open_pin", "open_50_lo", "open_50_hi", "open_90_lo", "open_90_hi",
        "nse_status", "nse_price", "nse_buy_qty", "nse_sell_qty",
        "close_pin", "close_50_lo", "close_50_hi", "close_90_lo", "close_90_hi", "close_typical_miss_rs",
        "window_start", "window_end", "high_pin", "high_50_lo", "high_50_hi", "high_90_lo", "high_90_hi", "low_pin", "low_50_lo", "low_50_hi", "low_90_lo", "low_90_hi",
        "typical_miss_high_rs", "typical_miss_low_rs", "day_high_so_far", "day_low_so_far",
        "bse_move_pct", "peers_move_pct", "peers_minus_bse_pp", "nifty_move_pct", "peers_valid", "remaining_move_to_close_pct",
        "compared_with", "this_hour_from", "this_hour_to",
        "this_hour_pred_high", "this_hour_actual_high", "this_hour_high_error_rs", "this_hour_high_in50", "this_hour_high_in90",
        "this_hour_pred_low", "this_hour_actual_low", "this_hour_low_error_rs", "this_hour_low_in50", "this_hour_low_in90",
        "window_actual_high", "window_actual_low", "window_high_error_rs", "window_low_error_rs", "window_high_in50", "window_high_in90", "window_low_in50", "window_low_in90",
        "official_open", "official_high", "official_low", "official_close",
        "open_error_rs", "open_in50", "open_in90", "close_error_rs", "close_in50", "close_in90", "note", "printed_row"]
ORDER = {"open_range": 0, "nse_preopen": 1, "day_high_low_pre_open": 2, "day_high_low_after_open": 3, "table": 4}


def _official() -> dict:
    fr = []
    for f in ("data/processed/bse_daily.csv", "data/processed/bse_daily_extra.csv"):
        if Path(f).exists():
            d = pd.read_csv(f, usecols=["date", "open", "high", "low", "close"]); fr.append(d)
    if not fr:
        return {}
    d = pd.concat(fr).drop_duplicates("date", keep="last").set_index("date")
    return {k: v for k, v in d.to_dict("index").items()}


def _in(v, lo, hi):
    return "" if v is None or lo is None or hi is None or pd.isna(v) else bool(lo <= v <= hi)


def _r(x, n=2):
    return "" if x is None or (isinstance(x, float) and pd.isna(x)) else round(float(x), n)


def _rows_open_range() -> list[dict]:
    out = []
    for f in sorted(glob.glob("results/scoreboard/entries/*.json")):
        e = json.loads(Path(f).read_text()); q = e["open"]["price"]; c = e["close"]["price"]
        out.append({"date": e["target_session"], "time_ist": e["made_at_ist"][11:19], "kind": "open_range", "source": f,
                    "open_pin": q["q0.5"], "open_50_lo": q["q0.25"], "open_50_hi": q["q0.75"], "open_90_lo": q["q0.05"], "open_90_hi": q["q0.95"],
                    "close_pin": c["q0.5"], "close_50_lo": c["q0.25"], "close_50_hi": c["q0.75"], "close_90_lo": c["q0.05"], "close_90_hi": c["q0.95"],
                    "note": f"previous close {e['reference_price']:,.1f} is the pin-point; lean: {e['lean']['direction_close']} for the close, {e['lean']['direction_open_to_close']} open to close (a lean, not a prediction)"})
    return out


def _rows_nse() -> list[dict]:
    import preopen as PO
    out, seen = [], set()
    for f in sorted(glob.glob("results/preopen/BSE_*.jsonl")):
        for l in Path(f).read_text().splitlines():
            if not l.strip():
                continue
            s = json.loads(l); p = s["pre"]; t = p["lastUpdateTime"]
            day = dt.datetime.strptime(t[:11], "%d-%b-%Y").strftime("%Y-%m-%d")
            if (day, t) in seen:                                               # the same NSE snapshot read twice (09:09 job and the table tool) is one reading
                continue
            seen.add((day, t))
            try:
                now = dt.datetime.fromisoformat(s["fetched_utc"]).astimezone(IST)
            except Exception:                                                  # noqa: BLE001
                now = dt.datetime.strptime(t[:11], "%d-%b-%Y").replace(hour=12, tzinfo=IST)
            st = s.get("status") or PO.status(s, now)
            fin = st == "FINAL"
            out.append({"date": day, "time_ist": t[-8:], "kind": "nse_preopen", "source": f, "open_pin": float(p["prevClose"]),
                        "nse_status": st, "nse_price": float(p["IEP"]), "nse_buy_qty": int(p["totalBuyQuantity"]), "nse_sell_qty": int(p["totalSellQuantity"]),
                        "note": "open_pin = previous close; the NSE price is the open itself only when nse_status is FINAL"})
    return out


def _band(q, lo, hi):
    return q.get(lo), q.get(hi)


def _rows_hl() -> list[dict]:
    out = []
    for f in sorted(glob.glob("results/hl_dayahead_*.json")):
        d = json.loads(Path(f).read_text()); mt = (d.get("saved_at_ist") or "")[11:19]       # file times are not trusted (a checkout rewrites them): only a time written into the file counts
        with_open = "_open" in Path(f).stem                                     # hl_dayahead_<date>_open<price>.json carries the pre-open block too: keep only its after-open part
        for kind, blk in (("day_high_low_pre_open", None if with_open else d.get("pre_open")), ("day_high_low_after_open", d.get("post_open"))):
            if not blk:
                continue
            h, l = blk["high"], blk["low"]; hq, lq = h["price_quantiles"], l["price_quantiles"]
            out.append({"date": d["date"], "time_ist": mt, "kind": kind, "source": f, "window_start": "09:15", "window_end": "15:30",
                        "open_pin": blk.get("open", ""), "close_pin": "",
                        "high_pin": hq["q50"], "high_50_lo": hq["q25"], "high_50_hi": hq["q75"], "high_90_lo": hq["q5"], "high_90_hi": hq["q95"],
                        "low_pin": lq["q50"], "low_50_lo": lq["q25"], "low_50_hi": lq["q75"], "low_90_lo": lq["q5"], "low_90_hi": lq["q95"],
                        "typical_miss_high_rs": h.get("typical_miss_rs"), "typical_miss_low_rs": l.get("typical_miss_rs"),
                        "note": "whole-day official high/low; time_ist is blank when the file does not record when it was saved; 'half the time' band = q25-q75; the 90% columns are q5-q95 (for the after-open high a 19-in-20 band: the open is the high on about 4% of days)"})
    return out


def _rows_table() -> list[dict]:
    import hourly_table as HT
    out = []
    p = Path(HT.LOG)
    if not p.exists():
        return out
    for l in p.read_text().splitlines():
        if not l.strip():
            continue
        r = json.loads(l)
        if r.get("mode") != "live":
            continue
        nh = r.get("next_hour") or {}
        th = r.get("this_hour") or {}
        tm = r.get("typical_miss_next_hour_rs") or [None, None]
        row = {"date": r["date"], "time_ist": r["asof"] + ":00", "kind": "table", "source": f"{HT.LOG} (logged {r.get('logged_utc', '')})", "price_now": r["price_now"],
               "close_pin": r["close_pin"], "close_50_lo": r["close_50"][0], "close_50_hi": r["close_50"][1], "close_90_lo": r["close_90"][0], "close_90_hi": r["close_90"][1],
               "close_typical_miss_rs": r["close_typical_miss_rs"], "day_high_so_far": r["day_high_so_far"], "day_low_so_far": r["day_low_so_far"],
               "typical_miss_high_rs": tm[0], "typical_miss_low_rs": tm[1], "compared_with": th.get("prediction_source", ""), "this_hour_from": th.get("from") or "", "this_hour_to": th.get("to") or ""}
        if nh:
            row.update({"window_start": nh["window_start"], "window_end": nh["window_end"],
                        "high_pin": nh["high"]["0.5"], "high_50_lo": nh["high"]["0.25"], "high_50_hi": nh["high"]["0.75"], "high_90_lo": nh["high"]["0.05"], "high_90_hi": nh["high"]["0.95"],
                        "low_pin": nh["low"]["0.5"], "low_50_lo": nh["low"]["0.25"], "low_50_hi": nh["low"]["0.75"], "low_90_lo": nh["low"]["0.05"], "low_90_hi": nh["low"]["0.95"]})
        pe = r.get("peers")                                                    # eighth column (forward test H), present from 22 Oct 2026; moves are 100 x ln(price / previous close)
        if pe and "error" not in pe:
            nf = (pe.get("symbols") or {}).get("NIFTY", {})
            row.update({"bse_move_pct": pe.get("bse_move_pct"), "peers_move_pct": (pe.get("P") or {}).get("move_pct"), "peers_minus_bse_pp": pe.get("gap_P_pp"),
                        "nifty_move_pct": nf.get("move_pct") if nf.get("status") == "ok" else "", "peers_valid": (pe.get("P") or {}).get("valid")})
        elif pe:
            row["peers_valid"] = False; row["note"] = ((row.get("note") or "") + " peers could not be read: " + str(pe.get("error"))).strip()
        for side in ("high", "low"):
            c = th.get(side)
            if c:
                row.update({f"this_hour_pred_{side}": c["predicted"], f"this_hour_actual_{side}": c["actual"], f"this_hour_{side}_error_rs": c["error_rs"], f"this_hour_{side}_in50": c["inside50"], f"this_hour_{side}_in90": c["inside90"]})
        try:
            row["printed_row"] = HT.fmt_row(r).split("\n")[2]
        except Exception:                                                      # noqa: BLE001
            row["printed_row"] = ""
        if (r.get("paper") or {}).get("error"):
            row["note"] = "paper ledger error at this reading: " + str(r["paper"]["error"])
        out.append(row)
    return out


def _attach_scores(rows: list[dict]) -> None:
    off = _official()
    sc = pd.read_csv("results/hourly_table_scored.csv") if Path("results/hourly_table_scored.csv").exists() else pd.DataFrame()
    for r in rows:
        o = off.get(r["date"])
        if o:
            r.update({"official_open": o["open"], "official_high": o["high"], "official_low": o["low"], "official_close": o["close"]})
            if r["kind"] == "table" and r.get("price_now") not in ("", None):
                r["remaining_move_to_close_pct"] = _r(100 * math.log(o["close"] / r["price_now"]), 3)       # the outcome R of forward test H: 100 x ln(official close / price now)
            if r["kind"] in ("open_range", "nse_preopen", "day_high_low_pre_open", "day_high_low_after_open", "table") and r.get("close_pin") not in ("", None):
                r["close_error_rs"] = _r(o["close"] - r["close_pin"], 1)
                if r.get("close_50_lo") not in ("", None):
                    r["close_in50"] = _in(o["close"], r["close_50_lo"], r["close_50_hi"]); r["close_in90"] = _in(o["close"], r["close_90_lo"], r["close_90_hi"])
            if r["kind"] == "open_range":
                r["open_error_rs"] = _r(o["open"] - r["open_pin"], 1); r["open_in50"] = _in(o["open"], r["open_50_lo"], r["open_50_hi"]); r["open_in90"] = _in(o["open"], r["open_90_lo"], r["open_90_hi"])
            if r["kind"] == "nse_preopen" and r["nse_status"] == "FINAL":
                r["open_error_rs"] = _r(o["open"] - r["nse_price"], 1)
            if r["kind"] == "day_high_low_after_open" and r.get("open_pin") not in ("", None) and abs(float(r["open_pin"]) - o["open"]) > 0.05:
                r["note"] = (str(r.get("note") or "") + f" DATA CORRECTION: this forecast was built on an open of Rs {float(r['open_pin']):,.1f}, which was NOT the official open (Rs {o['open']:,.1f}); it is kept as logged because it is what was given at the time.").strip()
            if r["kind"].startswith("day_high_low"):
                r.update({"window_actual_high": o["high"], "window_actual_low": o["low"], "window_high_error_rs": _r(o["high"] - r["high_pin"], 1), "window_low_error_rs": _r(o["low"] - r["low_pin"], 1),
                          "window_high_in50": _in(o["high"], r["high_50_lo"], r["high_50_hi"]), "window_high_in90": _in(o["high"], r["high_90_lo"], r["high_90_hi"]),
                          "window_low_in50": _in(o["low"], r["low_50_lo"], r["low_50_hi"]), "window_low_in90": _in(o["low"], r["low_90_lo"], r["low_90_hi"])})
        if r["kind"] == "table" and len(sc):
            m = sc[(sc["date"] == r["date"]) & (sc["asof"] == r["time_ist"][:5]) & (sc["mode"] == "live")]
            if len(m):
                m = m.iloc[0]
                r.update({"window_actual_high": m.act_high, "window_actual_low": m.act_low, "window_high_error_rs": _r(m.act_high - m.pred_high, 1), "window_low_error_rs": _r(m.act_low - m.pred_low, 1),
                          "window_high_in50": bool(m.high_in50), "window_high_in90": bool(m.high_in90), "window_low_in50": bool(m.low_in50), "window_low_in90": bool(m.low_in90)})


def rebuild() -> pd.DataFrame:
    rows = _rows_open_range() + _rows_nse() + _rows_hl() + _rows_table()
    _attach_scores(rows)
    df = pd.DataFrame(rows).reindex(columns=COLS)
    key = df.time_ist.fillna("").where(df.time_ist.fillna("") != "", df.kind.map({"day_high_low_pre_open": "08:36:59", "day_high_low_after_open": "09:09:59"}))   # ordering only; the stored time stays blank
    df["_k"] = key.fillna("99:99:99"); df["_o"] = df.kind.map(ORDER)
    df = df.sort_values(["date", "_k", "_o"], kind="stable").drop(columns=["_k", "_o"]).reset_index(drop=True)
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "by_day").mkdir(exist_ok=True)
    df.to_csv(OUT / "readings.csv", index=False)
    for d, g in df.groupby("date"):
        g.to_csv(OUT / "by_day" / f"{d}.csv", index=False)
    return df


if __name__ == "__main__":
    df = rebuild()
    print(f"results/readings/readings.csv: {len(df)} readings over {df.date.nunique()} day(s); " + ", ".join(f"{k} {v}" for k, v in df.kind.value_counts().items()) + "; per-day copies in results/readings/by_day/")

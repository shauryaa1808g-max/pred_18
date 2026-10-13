"""Score a stored forecast record against the realised official session.  Never edits the record.

Usage: python3 src/score_forecast.py results/forecast_record_2026-10-14.json   (after NSE publishes sec_bhavdata_full for the target date and build_dataset has been rerun)
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, "src")
from common import GRID, load_bse, targets
rec = json.loads(Path(sys.argv[1]).read_text())
d = load_bse(); t = targets(d)
day = pd.Timestamp(rec["target_session"])
force_udiff = "--force-udiff" in sys.argv
if day in d.index and not force_udiff:
    r = d.loc[day]
else:
    # fall back to the official NSE CM UDiFF bhavcopy for the target date (published ~16:34 IST); needs no raw history
    import requests
    from build_dataset import read_udiff
    from fetch_nse import CA, UA
    zp = Path("data/raw/udiff") / f"{day:%Y%m%d}.zip"
    if not zp.exists():
        zp.parent.mkdir(parents=True, exist_ok=True)
        resp = requests.get(f"https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{day:%Y%m%d}_F_0000.csv.zip", headers={"User-Agent": UA}, timeout=60, verify=CA)
        if resp.status_code != 200 or resp.content[:2] != b"PK":
            raise SystemExit(f"official file for {day.date()} not available yet (HTTP {resp.status_code}); NSE publishes it about 16:34 IST on the session day")
        zp.write_bytes(resp.content)
    u = read_udiff(zp)
    r = u[(u["symbol"] == "BSE") & (u["series"] == "EQ")].iloc[0]
P0 = rec["reference_price_P0"]
real = {"G": float(np.log(r["open"] / P0)), "I": float(np.log(r["close"] / r["open"])), "R": float(np.log(r["close"] / P0)),
        "Hp": float(np.log(r["high"] / P0)), "Lp": float(np.log(r["low"] / P0)), "rho": float(np.log(r["high"] / r["low"]))}
score = {"record": sys.argv[1], "target_session": rec["target_session"], "P0_in_record": P0, "P0_status": rec["reference_price_status"],
         "realised": {"open": float(r["open"]), "high": float(r["high"]), "low": float(r["low"]), "close": float(r["close"]), "volume": float(r["vol"])}, "realised_log": real, "targets": {}}
def pin(y, q): return float(np.mean(np.maximum(GRID * (y - q), (GRID - 1) * (y - q))))
for tg in ("G", "I", "R"):
    q = np.array([rec["log_return_quantiles"][tg][f"q{g:g}"] for g in GRID]); y = real[tg]
    pit = float(np.interp(y, q, GRID, left=0.0, right=1.0))
    score["targets"][tg] = {"y": y, "pinball": pin(y, q), "pit_approx": pit, "inside_50": bool(q[3] <= y <= q[5]), "inside_80": bool(q[2] <= y <= q[6]), "inside_90": bool(q[1] <= y <= q[7]), "inside_95": bool(q[0] <= y <= q[8])}
q = np.array([rec["log_return_quantiles"]["rho"][f"q{g:g}"] for g in GRID])
score["targets"]["rho"] = {"y": real["rho"], "pinball": pin(real["rho"], q), "inside_90": bool(q[1] <= real["rho"] <= q[7])}
for k, lab in (("Hp", "high"), ("Lp", "low")):
    q = np.array([rec["ohlc_bootstrap_log_quantiles"][k][f"q{g:g}"] for g in GRID]); y = real[k]
    score["targets"][k] = {"y": y, "pinball": pin(y, q), "inside_90": bool(q[1] <= y <= q[7]), "inside_50": bool(q[3] <= y <= q[5])}
sR = rec["log_return_quantiles"]["R"]["sigma"]
score["close_above_P0"] = bool(real["R"] > 0); score["brier_P_up_0.5"] = float((0.5 - (real["R"] > 0)) ** 2)
score["broadly_unchanged_|R|<0.25sigma"] = bool(abs(real["R"]) < 0.25 * sR); score["abs_R_over_sigma"] = float(abs(real["R"]) / sR)
out = Path(sys.argv[1]).with_name(Path(sys.argv[1]).name.replace("forecast_record", "forecast_score"))
out.write_text(json.dumps(score, indent=1)); print(json.dumps(score, indent=1))

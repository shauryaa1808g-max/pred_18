"""Small data logger / backfiller for the high-low study (specialist F).  Public GET requests only: no credentials, no logins.

Why it exists: several series that could (in principle) help the BSE high/low forecast exist ONLY as live 'today' snapshots (NSE pre-open book, FII/DII flows, option chain,
GIFT Nifty, indicative Nifty).  Nobody keeps their history for free, so we start keeping it ourselves.  See research/hl/F_data_availability.md.  Nothing here feeds any forecast.

LOGGERS (live snapshots, one JSON-lines.gz file per series per IST day under --out, default results/hl4_log/; each line = fetched_utc, ist, url, http, bytes, sha256, payload)
  python3 src/hl_fetch_extra.py snap-preopen    # 09:01, 09:04, 09:07, 09:09, 09:11 IST on trading days: NSE pre-open book (BSE + peers + totals) AND marketStatus (GIFT Nifty, indicative Nifty 50)
  python3 src/hl_fetch_extra.py snap-market     # marketStatus + allIndices only (India VIX, Nifty, sector indices); useful at 08:30 and 08:55 IST for the GIFT Nifty field
  python3 src/hl_fetch_extra.py snap-chain      # BSE option chain (all listed expiries, strikes, IV, OI, bid/ask; endpoint option-chain-v3): 09:20 and 15:25 IST are the useful times, 3-4 requests
  python3 src/hl_fetch_extra.py snap-eod        # once after ~19:45 IST: FII/DII cash flow, BSE option chain (final 15:40 snapshot), expiry list, board meetings, event calendar, participant-wise F&O OI/volume, FII derivative stats
  python3 src/hl_fetch_extra.py status          # what has been logged so far (flags files with a single line)

BACKFILLS / BUILDS (history that does exist)
  python3 src/hl_fetch_extra.py upstox --from 2022-01-03 --to 2026-10-15              # 15-minute bars for BSE (adjusted prices), ~58 monthly requests, 3 s apart
  python3 src/hl_fetch_extra.py upstox-index --symbol "India VIX" --from 2022-01-03 --to 2026-10-15 --csv results/hl4_upstox_15m_INDIAVIX.csv --meta results/hl4_upstox_15m_INDIAVIX_meta.json
  python3 src/hl_fetch_extra.py check-upstox                                           # compare the bars with the official NSE daily bar (needs the Upstox csv)
  python3 src/hl_fetch_extra.py events                                                 # BSE board-meeting / results calendar since 2017 with filing times (3 requests)
  python3 src/hl_fetch_extra.py participant --last 30                                  # participant-wise F&O OI + volume (FII/DII/Pro/Client) for the last N sessions; or --from/--to
  python3 src/hl_fetch_extra.py fo-expiries                                            # BSE stock-F&O expiry dates from the local bhavcopy cache + NSE's live expiry list

Suggested schedule (cron, TZ=Asia/Kolkata, Mon-Fri; on an exchange holiday the live endpoints just repeat the last session, `status` shows it):
  1,4,7,9,11 9 * * 1-5   python3 src/hl_fetch_extra.py snap-preopen
  30,55 8 * * 1-5        python3 src/hl_fetch_extra.py snap-market
  20 9 * * 1-5           python3 src/hl_fetch_extra.py snap-chain
  25 15 * * 1-5          python3 src/hl_fetch_extra.py snap-chain
  45 19 * * 1-5          python3 src/hl_fetch_extra.py snap-eod
Be polite: each run makes 1-10 requests; NSE endpoints need the cookie warm-up the script does; never loop it faster than once per minute.
"""
from __future__ import annotations

import argparse
import calendar
import csv
import datetime as dt
import glob
import gzip
import hashlib
import io
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
JAR = "/tmp/nse_cookies_hl4.txt"
PEERS = ["BSE", "CDSL", "MCX", "ANGELONE", "CAMS", "KFINTECH", "NUVAMA", "360ONE", "IEX"]          # pre-open rows kept (the full list is ~2 MB per call; --keep-all keeps everything)
UPSTOX = "https://api.upstox.com/v3/historical-candle"
UPSTOX_KEYS = {"BSE": "NSE_EQ%7CINE118H01025", "Nifty 50": "NSE_INDEX%7CNifty%2050", "India VIX": "NSE_INDEX%7CIndia%20VIX", "Nifty Bank": "NSE_INDEX%7CNifty%20Bank"}
CUTOFF = "2026-10-15"                                                                             # nothing later is ever written to a results file by the builders below


def now_ist() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).astimezone(IST)


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ------------------------------------------------------------------------------------------------------------------------------------ transport
def curl(url: str, nse: bool = False, timeout: int = 40, headers: tuple = ()) -> tuple[int, bytes, dict]:
    """GET through the sandbox proxy with curl.  Returns (http_code, body, response_headers_lowercased)."""
    with tempfile.TemporaryDirectory() as td:
        bp, hp = os.path.join(td, "b"), os.path.join(td, "h")
        cmd = ["curl", "-sS", "--http1.1", "-m", str(timeout), "-A", UA, "-o", bp, "-D", hp, "-w", "%{http_code}"]
        if nse:
            cmd += ["-b", JAR, "-H", "Accept: application/json, text/plain, */*", "-H", "Referer: https://www.nseindia.com/"]
        for h in headers:
            cmd += ["-H", h]
        r = subprocess.run(cmd + [url], capture_output=True, text=True)
        body = open(bp, "rb").read() if os.path.exists(bp) else b""
        hdr = {}
        if os.path.exists(hp):
            for line in open(hp, encoding="latin-1"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    hdr[k.strip().lower()] = v.strip()
        return (int(r.stdout.strip()) if r.stdout.strip().isdigit() else 0), body, hdr


def nse_warm() -> None:
    """One visit to the NSE home page to get cookies (the page itself may answer 403; the cookies are still set)."""
    subprocess.run(["curl", "-sS", "--http1.1", "-m", "25", "-A", UA, "-c", JAR, "-o", "/dev/null", "https://www.nseindia.com/"], capture_output=True)


def nse_json(url: str, tries: int = 3):
    last = None
    for k in range(tries):
        code, body, _ = curl(url, nse=True)
        try:
            return code, body, json.loads(body)
        except Exception as e:                                                                  # noqa: BLE001
            last = f"HTTP {code}: {e}"
            nse_warm(); time.sleep(2 + 2 * k)
    return 0, b"", {"error": last}


def log_line(out: Path, series: str, url: str, http: int, body: bytes, payload) -> Path:
    t = now_ist()
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"{series}_{t:%Y-%m-%d}.jsonl.gz"
    rec = {"fetched_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "ist": t.strftime("%Y-%m-%d %H:%M:%S"), "url": url, "http": http, "bytes": len(body),
           "sha256": sha(body), "payload": payload}
    with gzip.open(p, "at", encoding="utf8") as f:
        f.write(json.dumps(rec, separators=(",", ":")) + "\n")
    return p


# ------------------------------------------------------------------------------------------------------------------------------------ live snapshots
def snap_market(out: Path) -> None:
    """marketStatus carries 'giftnifty' (GIFT Nifty last price + timestamp while it trades) and 'indicativenifty50' (indicative Nifty during the pre-open).  Both were null on Sat 17 Oct 2026."""
    nse_warm()
    for name, url in (("marketStatus", "https://www.nseindia.com/api/marketStatus"), ("allIndices", "https://www.nseindia.com/api/allIndices")):
        code, body, j = nse_json(url)
        p = log_line(out, name, url, code, body, j)
        g = j.get("giftnifty") if isinstance(j, dict) else None
        print(f"{name}: HTTP {code}, {len(body)} bytes, giftnifty={g.get('LASTPRICE') if g else None} -> {p}")
        time.sleep(1.5)


def snap_preopen(out: Path, keep_all: bool = False) -> None:
    """NSE pre-open book (unofficial API, same endpoint as src/preopen.py).  Keeps BSE and the peer rows with the full price ladder, plus market totals; also logs marketStatus."""
    nse_warm()
    url = "https://www.nseindia.com/api/market-data-pre-open?key=ALL"
    code, body, j = nse_json(url)
    if not isinstance(j, dict) or "data" not in j:
        print("preopen: no data", str(j)[:200]); return
    rows = [r for r in j["data"] if keep_all or r["metadata"]["symbol"] in PEERS]
    payload = {"timestamp": j.get("timestamp"), "advances": j.get("advances"), "declines": j.get("declines"), "unchanged": j.get("unchanged"), "totalTradedValue": j.get("totalTradedValue"),
               "totalTradedVolume": j.get("totalTradedVolume"), "rows": rows}
    p = log_line(out, "preopen", url, code, body, payload)
    b = next((r for r in rows if r["metadata"]["symbol"] == "BSE"), None)
    print(f"preopen {j.get('timestamp')}: BSE IEP {b['detail']['preOpenMarket']['IEP'] if b else 'n/a'} -> {p}")
    url2 = "https://www.nseindia.com/api/marketStatus"
    code2, body2, j2 = nse_json(url2)
    log_line(out, "marketStatus", url2, code2, body2, j2)


def snap_chain(out: Path) -> None:
    """BSE option chain via option-chain-v3 (the older option-chain-equities answered '{}' on 17 Oct 2026).  One call per listed expiry (usually 3).  Records: strike, CE/PE last, bid/ask,
    impliedVolatility, openInterest, volumes; 'records.timestamp' is the snapshot time on NSE's side."""
    nse_warm()
    ci_url = "https://www.nseindia.com/api/option-chain-contract-info?symbol=BSE"
    code, body, ci = nse_json(ci_url)
    log_line(out, "contract_info_BSE", ci_url, code, body, ci)
    for ex in (ci.get("expiryDates") or []) if isinstance(ci, dict) else []:
        url = f"https://www.nseindia.com/api/option-chain-v3?type=Equity&symbol=BSE&expiry={ex}"
        c2, b2, j = nse_json(url)
        p = log_line(out, "optchain_v3_BSE", url, c2, b2, j)
        print(f"optchain {ex}: HTTP {c2}, {len(b2)} bytes, snapshot {j.get('records', {}).get('timestamp') if isinstance(j, dict) else None} -> {p}")
        time.sleep(2)


EOD_JSON = {
    "fiidii": "https://www.nseindia.com/api/fiidiiTradeReact",                                  # cash-market FII/DII net, latest session only (no history on this endpoint)
    "board_meetings_BSE": "https://www.nseindia.com/api/corporate-board-meetings?index=equities&symbol=BSE",
    "event_calendar_BSE": "https://www.nseindia.com/api/event-calendar?symbol=BSE",
}


def snap_eod(out: Path) -> None:
    nse_warm()
    for name, url in EOD_JSON.items():
        code, body, j = nse_json(url)
        p = log_line(out, name, url, code, body, j)
        print(f"{name}: HTTP {code}, {len(body)} bytes -> {p}")
        time.sleep(2)
    snap_chain(out)
    d = now_ist()
    for name, url in {"participant_oi": f"https://nsearchives.nseindia.com/content/nsccl/fao_participant_oi_{d:%d%m%Y}.csv",
                      "participant_vol": f"https://nsearchives.nseindia.com/content/nsccl/fao_participant_vol_{d:%d%m%Y}.csv",
                      "fii_stats": f"https://nsearchives.nseindia.com/content/fo/fii_stats_{d:%d-%b-%Y}.xls"}.items():
        code, body, hdr = curl(url)
        pay = {"last_modified": hdr.get("last-modified"), **({"text": body.decode("utf8", "replace")} if name != "fii_stats" and code == 200 else {"note": "binary xls: sha256 only" if code == 200 else "not available"})}
        p = log_line(out, name, url, code, body, pay)
        print(f"{name}: HTTP {code}, {len(body)} bytes -> {p}")
        time.sleep(2)


def payload_stamp(p) -> str:
    """The exchange-side time stamp inside a payload, if one can be found (used by `status` to flag stale snapshots, e.g. on holidays or weekends)."""
    try:
        if isinstance(p, list) and p and isinstance(p[-1], dict) and p[-1].get("date"):
            return str(p[-1]["date"])
        if not isinstance(p, dict):
            return ""
        for k in ("timestamp",):
            if p.get(k):
                return str(p[k])
        if isinstance(p.get("records"), dict) and p["records"].get("timestamp"):
            return str(p["records"]["timestamp"])
        if isinstance(p.get("marketState"), list) and p["marketState"]:
            return str(p["marketState"][0].get("tradeDate", ""))
    except Exception:                                                                           # noqa: BLE001
        pass
    return ""


def status(out: Path) -> None:
    if not out.exists():
        print("nothing logged yet:", out); return
    for p in sorted(out.glob("*.jsonl.gz")):
        lines = [json.loads(l) for l in gzip.open(p, "rt")]
        day = p.name.split("_")[-1][:10]
        st = payload_stamp(lines[-1]["payload"]) if lines else ""
        try:
            sd = dt.datetime.strptime(st[:11], "%d-%b-%Y").strftime("%Y-%m-%d")
        except ValueError:
            sd = ""
        flag = "  STALE (exchange stamp %s != file day %s)" % (sd, day) if sd and sd != day else ""
        print(f"{p.name:50s} {len(lines):3d} line(s)  last exchange stamp: {st or 'n/a'}{flag}")


# ------------------------------------------------------------------------------------------------------------------------------------ Upstox bars (BSE and indices)
def month_windows(start: dt.date, end: dt.date):
    d = start
    while d <= end:
        last = dt.date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])
        yield d, min(last, end)
        d = last + dt.timedelta(days=1)


def upstox(symbol: str, start: dt.date, end: dt.date, interval: int, csv_path: Path, meta_path: Path, pause: float) -> None:
    """Unauthenticated public GET of Upstox's historical-candle endpoint (v3), monthly windows (the 1-15 minute limit is one month per request).
    NOTE: Upstox's documentation says a bearer token is required; the endpoint nevertheless answered without one when tested on 17 Oct 2026.  Treat as tolerated, not guaranteed.
    BSE prices are adjusted for later bonus issues (factor 9 before mid-2022, 3 until May 2025, 1 after): see check-upstox."""
    import pandas as pd
    key = UPSTOX_KEYS[symbol]
    rows, metas = [], []
    for a, b in month_windows(start, end):
        url = f"{UPSTOX}/{key}/minutes/{interval}/{b:%Y-%m-%d}/{a:%Y-%m-%d}"
        for k in range(4):
            code, body, _ = curl(url, timeout=40)
            if code == 200:
                break
            time.sleep(5 * (k + 1))
        n = 0
        if code == 200:
            for t, o, h, l, c, v, _oi in json.loads(body)["data"]["candles"]:
                rows.append((t[:10], t[11:16], o, h, l, c, v)); n += 1
        metas.append({"url": url, "http": code, "retrieved_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "bytes": len(body), "sha256": sha(body), "bars": n})
        print(a, b, code, n, flush=True)
        time.sleep(pause)
    df = pd.DataFrame(rows, columns=["date", "time", "open", "high", "low", "close", "volume"]).sort_values(["date", "time"]).drop_duplicates(["date", "time"])
    df = df[df.date <= end.strftime("%Y-%m-%d")]
    df.to_csv(csv_path, index=False)
    meta = {"source": f"api.upstox.com v3 historical-candle, instrument {key}, unauthenticated public GET", "symbol": symbol, "interval_minutes": interval, "window": [str(start), str(end)],
            "rows": len(df), "sessions": int(df.date.nunique()), "csv_sha256": sha(Path(csv_path).read_bytes()), "requests": metas,
            "prices": "as served (BSE: adjusted for later corporate actions; indices unadjusted); volume in shares (indices: 0)"}
    Path(meta_path).write_text(json.dumps(meta, indent=1))
    print("wrote", csv_path, len(df), "rows,", df.date.nunique(), "sessions")


def official_daily(end: str = CUTOFF):
    """Official NSE daily bar for BSE from the project's files, capped at `end` (the 16 Oct row in bse_daily_extra.csv is never read)."""
    import pandas as pd
    parts = [pd.read_csv("data/processed/bse_daily.csv"), pd.read_csv("data/processed/bse_daily_extra.csv")]
    d = pd.concat([p[["date", "open", "high", "low", "close", "vol"]] for p in parts]).drop_duplicates("date", keep="first")
    d["date"] = pd.to_datetime(d["date"]).dt.strftime("%Y-%m-%d")
    return d[d.date <= end].set_index("date").sort_index()


def check_upstox(csv_path: Path, out_csv: Path, out_json: Path) -> None:
    """Per session: Upstox 15-minute bars aggregated to O/H/L/C and multiplied by the snapped adjustment factor (1, 3 or 9), against the official NSE bar (raw traded prices)."""
    import numpy as np
    import pandas as pd
    u = pd.read_csv(csv_path)
    g = u.groupby("date").agg(bars=("high", "size"), uh=("high", "max"), ul=("low", "min"), uvol=("volume", "sum"))
    g["uo"] = u.groupby("date").open.first(); g["uc"] = u.groupby("date").close.last()
    off = official_daily()
    j = g.join(off, how="left")
    ratio = j.close / j.uc
    j["factor"] = np.where(ratio.isna(), np.nan, np.array([1.0, 3.0, 9.0])[np.abs(np.log(ratio.fillna(1.0).values[:, None] / np.array([1.0, 3.0, 9.0])[None, :])).argmin(1)])
    j["h_adj"] = j.uh * j.factor; j["l_adj"] = j.ul * j.factor; j["o_adj"] = j.uo * j.factor; j["c_adj"] = j.uc * j.factor
    for k, a, b in (("open", "o_adj", "open"), ("high", "h_adj", "high"), ("low", "l_adj", "low"), ("close", "c_adj", "close")):
        j[f"err_{k}_rs"] = j[a] - j[b]; j[f"err_{k}_pct"] = 100 * (j[a] / j[b] - 1)
    j["volume_ratio"] = j.uvol / j.vol                                                           # shares: Upstox volume is NOT adjusted for the bonus, official volume is raw: ratio ~ 1 means raw
    j["is_official_session"] = j.close.notna()
    j.reset_index().to_csv(out_csv, index=False, float_format="%.4f")
    o = j[j.is_official_session].copy()
    o["era"] = o.factor.map({9.0: "factor 9 (to mid-2022)", 3.0: "factor 3 (mid-2022 to May 2025)", 1.0: "factor 1 (after May 2025)"})
    summ = {"sessions_upstox": int(len(j)), "sessions_official": int(o.shape[0]), "special_sessions_not_in_official": [d for d in j.index[~j.is_official_session]],
            "bars_per_session_counts": {int(k): int(v) for k, v in j.bars.value_counts().items()}, "eras": {}}
    for era, x in o.groupby("era"):
        summ["eras"][era] = {"n": int(len(x)), "first": x.index.min(), "last": x.index.max(),
                             "high_abs_err_rs_median": float(x.err_high_rs.abs().median()), "high_abs_err_rs_max": float(x.err_high_rs.abs().max()),
                             "low_abs_err_rs_median": float(x.err_low_rs.abs().median()), "low_abs_err_rs_max": float(x.err_low_rs.abs().max()),
                             "high_abs_err_pct_median": float(x.err_high_pct.abs().median()), "high_abs_err_pct_max": float(x.err_high_pct.abs().max()),
                             "low_abs_err_pct_median": float(x.err_low_pct.abs().median()), "low_abs_err_pct_max": float(x.err_low_pct.abs().max()),
                             "share_high_within_0.05rs": float((x.err_high_rs.abs() <= 0.051).mean()), "share_low_within_0.05rs": float((x.err_low_rs.abs() <= 0.051).mean()),
                             "share_close_within_0.05rs": float((x.err_close_rs.abs() <= 0.051).mean()), "share_open_within_0.05rs": float((x.err_open_rs.abs() <= 0.051).mean())}
    post = o[o.index >= "2026-08-03"]
    summ["post_closing_auction_since_2026-08-03"] = {"n": int(len(post)), "share_close_within_0.05rs": float((post.err_close_rs.abs() <= 0.051).mean()),
                                                     "share_high_within_0.05rs": float((post.err_high_rs.abs() <= 0.051).mean()), "share_low_within_0.05rs": float((post.err_low_rs.abs() <= 0.051).mean())}
    Path(out_json).write_text(json.dumps(summ, indent=1))
    print(json.dumps(summ, indent=1)[:3000])


# ------------------------------------------------------------------------------------------------------------------------------------ BSE results / board-meeting calendar
def events(out_csv: Path, out_json: Path) -> None:
    """NSE event-calendar (all BSE board meetings since 2017), board-meetings feed (intimation timestamps, last ~20), corporate-announcements (filing times of the outcomes).  3 requests.
    Announcement rows stamped after 15 Oct 2026 22:00 IST are dropped before anything is derived."""
    nse_warm()
    srcs = {"event_calendar": "https://www.nseindia.com/api/event-calendar?symbol=BSE", "board_meetings": "https://www.nseindia.com/api/corporate-board-meetings?index=equities&symbol=BSE",
            "announcements": "https://www.nseindia.com/api/corporate-announcements?index=equities&symbol=BSE"}
    raw, meta = {}, {}
    for k, url in srcs.items():
        code, body, j = nse_json(url)
        raw[k] = j
        meta[k] = {"url": url, "http": code, "bytes": len(body), "sha256": sha(body), "retrieved_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
        time.sleep(2)
    cut = dt.datetime.strptime(CUTOFF + " 22:00:00", "%Y-%m-%d %H:%M:%S")
    ann = []
    for r in raw["announcements"]:
        t = dt.datetime.strptime(r["an_dt"], "%d-%b-%Y %H:%M:%S")
        if t <= cut and r["desc"] in ("Outcome of Board Meeting", "Financial Result Updates"):
            ann.append((t, r["desc"], r.get("attchmntFile")))
    bm = {}
    for r in raw["board_meetings"]:
        bm.setdefault(r["bm_date"], []).append(r["bm_timestamp"])
    sessions = sorted(official_daily().index)
    rows = []
    for e in sorted(raw["event_calendar"], key=lambda r: dt.datetime.strptime(r["date"], "%d-%b-%Y")):
        d = dt.datetime.strptime(e["date"], "%d-%b-%Y").date()
        same = sorted([a for a in ann if a[0].date() == d])
        first = same[0] if same else None
        nxt = next((s for s in sessions if s > str(d)), "")
        is_res = e["purpose"].lower().startswith(("result", "financial result"))
        rows.append({"meeting_date": str(d), "weekday": d.strftime("%a"), "purpose": e["purpose"], "is_results": is_res, "since_2022": str(d) >= "2022-01-01",
                     "first_outcome_filing_ist": first[0].strftime("%Y-%m-%d %H:%M:%S") if first else "", "first_filing_kind": first[1] if first else "",
                     "filed_after_1530": (first[0].time() >= dt.time(15, 30)) if first else "", "next_session_after_meeting": nxt if str(d) <= CUTOFF else "",
                     "intimation_ist_earliest": min(bm[d.strftime("%d-%b-%Y")]) if d.strftime("%d-%b-%Y") in bm else "", "outcome_pdf": first[2] if first else "",
                     "future_as_of_cutoff": str(d) > CUTOFF})
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    meta["note"] = "announcement rows stamped after 2026-10-15 22:00 IST dropped; raw announcements JSON (830 KB) not stored, sha256 only; csv sha256 below"
    meta["csv_sha256"] = sha(Path(out_csv).read_bytes()); meta["rows"] = len(rows)
    Path(out_json).write_text(json.dumps(meta, indent=1))
    print("wrote", out_csv, len(rows), "rows")


# ------------------------------------------------------------------------------------------------------------------------------------ participant-wise F&O positions (FII / DII / Pro / Client)
def parse_participant(text: str):
    rows = list(csv.reader(io.StringIO(text.replace('""', '"'))))
    head = [h.strip() for h in rows[1]]
    return [dict(zip(head, [c.strip() for c in r])) for r in rows[2:] if r and r[0].strip()]


def participant(dates: list[str], out_csv: Path, out_json: Path, pause: float) -> None:
    allrows, metas = [], []
    for d in dates:
        k = d.replace("-", "")
        key = f"{k[6:8]}{k[4:6]}{k[0:4]}"
        for kind, stem in (("oi", "fao_participant_oi"), ("vol", "fao_participant_vol")):
            url = f"https://nsearchives.nseindia.com/content/nsccl/{stem}_{key}.csv"
            for k_try in range(3):                                                              # transient curl failures (code 0) and 5xx are retried; 404 (holiday / not yet published) is not
                code, body, hdr = curl(url, timeout=30)
                if code == 200 or code == 404:
                    break
                time.sleep(3 * (k_try + 1))
            lm = hdr.get("last-modified", "")
            metas.append({"date": d, "kind": kind, "url": url, "http": code, "bytes": len(body), "sha256": sha(body), "last_modified": lm, "retrieved_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
            if code == 200:
                for r in parse_participant(body.decode("utf8", "replace")):
                    allrows.append({"date": d, "kind": kind, "file_last_modified_gmt": lm, **r})
            time.sleep(pause)
        print(d, flush=True)
    cols = ["date", "kind", "file_last_modified_gmt"] + [c for c in allrows[0] if c not in ("date", "kind", "file_last_modified_gmt")]
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(allrows)
    Path(out_json).write_text(json.dumps({"source": "nsearchives.nseindia.com/content/nsccl/fao_participant_{oi,vol}_DDMMYYYY.csv", "files": len(metas), "rows": len(allrows), "csv_sha256": sha(Path(out_csv).read_bytes()), "requests": metas}, indent=1))
    print("wrote", out_csv, len(allrows), "rows")


# ------------------------------------------------------------------------------------------------------------------------------------ F&O expiry calendar for BSE stock derivatives
def fo_expiries(out_csv: Path, out_json: Path) -> None:
    import pandas as pd
    files = sorted(glob.glob("data/raw/fo_bse/*.csv")) + sorted(glob.glob("results/hl2_fill_fo_2026*.csv"))
    seen = {}
    for f in files:
        d8 = Path(f).stem.split("_")[-1][:8]
        if d8 > CUTOFF.replace("-", ""):
            continue
        try:
            x = pd.read_csv(f, usecols=["XpryDt"])
        except Exception:                                                                       # noqa: BLE001  (empty files before BSE was listed)
            continue
        for e in x.XpryDt.dropna().unique():
            s = seen.setdefault(str(e), [d8, d8, 0]); s[0] = min(s[0], d8); s[1] = max(s[1], d8); s[2] += 1
    nse_warm()
    code, body, j = nse_json("https://www.nseindia.com/api/option-chain-contract-info?symbol=BSE")
    live = [dt.datetime.strptime(e, "%d-%b-%Y").strftime("%Y-%m-%d") for e in j.get("expiryDates", [])] if isinstance(j, dict) else []
    rows = []
    for e in sorted(set(seen) | set(live)):
        d = dt.date.fromisoformat(e)
        last_dow = lambda dow: max(x for x in (dt.date(d.year, d.month, i) for i in range(1, calendar.monthrange(d.year, d.month)[1] + 1)) if x.weekday() == dow)  # noqa: E731
        rule = "last Thursday" if d == last_dow(3) else "last Tuesday" if d == last_dow(1) else "other (holiday shift)"
        fs = seen.get(e)
        rows.append({"expiry": e, "weekday": d.strftime("%a"), "calendar_rule_match": rule, "first_seen_session": fs[0] if fs else "", "last_seen_session": fs[1] if fs else "",
                     "sessions_listed_in_cache": fs[2] if fs else "", "in_nse_live_contract_info": e in live})
    pd.DataFrame(rows).to_csv(out_csv, index=False)
    Path(out_json).write_text(json.dumps({"sources": ["data/raw/fo_bse/*.csv (NSE F&O UDiFF bhavcopy, BSE rows)", "results/hl2_fill_fo_2026*.csv", "https://www.nseindia.com/api/option-chain-contract-info?symbol=BSE"],
                                          "nse_live_http": code, "nse_live_sha256": sha(body), "retrieved_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "nse_live_expiries": live, "rows": len(rows),
                                          "csv_sha256": sha(Path(out_csv).read_bytes())}, indent=1))
    print(pd.DataFrame(rows).to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["snap-preopen", "snap-market", "snap-chain", "snap-eod", "status", "upstox", "upstox-index", "check-upstox", "events", "participant", "fo-expiries"])
    ap.add_argument("--out", default="results/hl4_log"); ap.add_argument("--keep-all", action="store_true", help="snap-preopen: keep all ~2,100 rows (about 2 MB per call)")
    ap.add_argument("--from", dest="frm", default="2022-01-03"); ap.add_argument("--to", default=CUTOFF); ap.add_argument("--last", type=int, default=0, help="participant: last N sessions up to --to")
    ap.add_argument("--symbol", default="BSE", choices=list(UPSTOX_KEYS)); ap.add_argument("--interval", type=int, default=15); ap.add_argument("--pause", type=float, default=3.0)
    ap.add_argument("--csv", default=None); ap.add_argument("--meta", default=None)
    a = ap.parse_args()
    out = Path(a.out)
    if a.to > CUTOFF and a.cmd in ("upstox", "upstox-index", "participant"):
        raise SystemExit(f"--to {a.to} is after the study cutoff {CUTOFF}: refused (this module never writes later data into results files)")
    if a.cmd == "snap-preopen":
        snap_preopen(out, a.keep_all)
    elif a.cmd == "snap-market":
        snap_market(out)
    elif a.cmd == "snap-chain":
        snap_chain(out)
    elif a.cmd == "snap-eod":
        snap_eod(out)
    elif a.cmd == "status":
        status(out)
    elif a.cmd in ("upstox", "upstox-index"):
        sym = "BSE" if a.cmd == "upstox" else a.symbol
        upstox(sym, dt.date.fromisoformat(a.frm), dt.date.fromisoformat(a.to), a.interval, Path(a.csv or "results/hl4_upstox_15m_BSE.csv"), Path(a.meta or "results/hl4_upstox_15m_meta.json"), a.pause)
    elif a.cmd == "check-upstox":
        check_upstox(Path(a.csv or "results/hl4_upstox_15m_BSE.csv"), Path("results/hl4_upstox_check.csv"), Path("results/hl4_upstox_check_summary.json"))
    elif a.cmd == "events":
        events(Path(a.csv or "results/hl4_bse_event_calendar.csv"), Path(a.meta or "results/hl4_bse_event_calendar_meta.json"))
    elif a.cmd == "participant":
        ses = [s for s in official_daily(a.to).index]
        ses = ses[-a.last:] if a.last else [s for s in ses if a.frm <= s <= a.to]
        participant(ses, Path(a.csv or "results/hl4_participant_oi_vol.csv"), Path(a.meta or "results/hl4_participant_oi_vol_meta.json"), a.pause)
    elif a.cmd == "fo-expiries":
        fo_expiries(Path(a.csv or "results/hl4_fo_expiry_calendar.csv"), Path(a.meta or "results/hl4_fo_expiry_calendar_meta.json"))

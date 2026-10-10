"""Download regular-hours bars from Twelve Data (rotating the keys in quant-platform backend/.env, never
printed) and write Foresight-format CSVs: data/<TF>/<SYM>.csv. Resumable: existing files are skipped."""
import re, sys, time, json, itertools
from pathlib import Path
import pandas as pd, httpx

ROOT = Path(__file__).parent
env = Path(r"C:\Users\annev\Downloads\quant-platform-full\backend\.env").read_text(encoding="utf-8")
KEYS = re.findall(r"^TWELVEDATA_API_KEY\w*\s*=\s*['\"]?([^'\"\s]+)", env, re.M)
keyc = itertools.cycle(KEYS)
WL = json.load(open(r"C:\Users\annev\workspace\backtest-results-dashboard\config\watchlists.json"))["watchlists"]
TICKERS = sorted({t for w in WL for t in w["tickers"]} | {"SPY", "IWM"})
TFS = {"5m": ("5min", "2024-10-01", 5), "15m": ("15min", "2022-10-01", 15), "1h": ("1h", "2018-10-01", 60), "daily": ("1day", "2010-01-01", 0)}
last_call = [0.0]

def page(sym, iv, end=None):
    for attempt in range(len(KEYS) * 6):
        gap = 60 / (8 * len(KEYS)) - (time.time() - last_call[0])     # stay under 8 calls/min/key
        if gap > 0: time.sleep(gap)
        last_call[0] = time.time()
        p = {"symbol": sym, "interval": iv, "outputsize": 5000, "timezone": "America/New_York", "apikey": next(keyc)}
        if end: p["end_date"] = end
        try: b = httpx.get("https://api.twelvedata.com/time_series", params=p, timeout=60).json()
        except Exception: time.sleep(5); continue
        if b.get("status") == "error":
            msg = b.get("message", "")
            if "credits" in msg or "limit" in msg.lower(): time.sleep(8); continue
            if "No data" in msg or "not found" in msg.lower() or "symbol" in msg.lower(): return None
            raise RuntimeError(msg[:120])
        return b.get("values", [])
    raise RuntimeError("rate-limited on every key")

def full(sym, iv, start):
    rows, end = [], None
    while True:
        v = page(sym, iv, end)
        if v is None: return None
        if not v: break
        rows += v
        first = v[-1]["datetime"]
        if first <= start or len(v) < 5000: break
        end = (pd.Timestamp(first) - pd.Timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")
    if not rows: return None
    df = pd.DataFrame(rows).drop_duplicates("datetime")
    df["dt"] = pd.to_datetime(df.datetime)
    for k in ("open", "high", "low", "close", "volume"):
        df[k] = pd.to_numeric(df[k], errors="coerce") if k in df else 0.0
    df = df.sort_values("dt")
    return df[df.dt >= start].dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)

def to_foresight(df, sym, minutes):
    if minutes:   # intraday: regular hours only, timestamps to UTC
        t = df.dt.dt.time
        df = df[(t >= pd.Timestamp("09:30").time()) & (t < pd.Timestamp("16:00").time())]
        utc = df.dt.dt.tz_localize("America/New_York").dt.tz_convert("UTC")
        close_ms = (utc + pd.Timedelta(minutes=minutes) - pd.Timestamp(0, tz="UTC")) // pd.Timedelta(milliseconds=1)
    else:         # daily: stamp the session open, close at 16:00 New York
        utc = (df.dt + pd.Timedelta(hours=9, minutes=30)).dt.tz_localize("America/New_York").dt.tz_convert("UTC")
        close_ms = ((df.dt + pd.Timedelta(hours=16)).dt.tz_localize("America/New_York").dt.tz_convert("UTC") - pd.Timestamp(0, tz="UTC")) // pd.Timedelta(milliseconds=1)
    return pd.DataFrame({"instrument": sym, "date": utc.dt.strftime("%Y-%m-%d"), "time_of_day": utc.dt.strftime("%H:%M:%S"),
                         "open": df.open.values, "high": df.high.values, "low": df.low.values, "close": df.close.values,
                         "volume": df.volume.fillna(0).astype("int64").values, "close_time": close_ms.values, "mintick": 0.01,
                         "exchange_timezone": "America/New_York", "pointvalue": 1, "mincontract": 1})

if __name__ == "__main__":
    tfs = sys.argv[1:] or list(TFS)
    print(len(KEYS), "keys;", len(TICKERS), "tickers;", tfs, flush=True)
    for tf in tfs:
        iv, start, mins = TFS[tf]; (ROOT / "data" / tf).mkdir(parents=True, exist_ok=True)
        for sym in TICKERS:
            out = ROOT / "data" / tf / f"{sym}.csv"; miss = out.with_suffix(".missing")
            if out.exists() or miss.exists(): continue
            try:
                df = full(sym, iv, start)
                if df is None or len(df) < 50: miss.write_text("no data"); print(tf, sym, "NO DATA", flush=True); continue
                f = to_foresight(df, sym, mins); tmp = out.with_suffix(".tmp"); f.to_csv(tmp, index=False); tmp.replace(out)
                print(f"{tf:5s} {sym:5s} {len(f):6d} bars {f.date.iloc[0]}..{f.date.iloc[-1]}", flush=True)
            except Exception as e:
                print(tf, sym, "ERROR", e, flush=True)
    if not sys.argv[1:] or sys.argv[1:] == ["daily", "1h", "15m", "5m"]:
        (ROOT / "fetch.finished").write_text(time.strftime("%Y-%m-%d %H:%M"))

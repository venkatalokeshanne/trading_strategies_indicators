"""Twelve Data 1-min client: key rotation, per-key backoff, resumable, parquet per symbol/month."""
import json
import os
import time
from datetime import date, datetime, timedelta

import pandas as pd
import requests

URL = "https://api.twelvedata.com/time_series"
TZ = "America/New_York"
COLS = ["time", "open", "high", "low", "close", "volume"]


class Keys:
    def __init__(self, keys: list[str]):
        self.keys, self.cool, self.i = keys, {k: 0.0 for k in keys}, 0

    def get(self) -> str:
        while True:
            now = time.time()
            for _ in self.keys:
                k = self.keys[self.i % len(self.keys)]
                self.i += 1
                if self.cool[k] <= now:
                    return k
            time.sleep(max(0.5, min(self.cool.values()) - now))

    def back_off(self, k: str, secs: float) -> None:
        self.cool[k] = time.time() + secs


def _request(keys: Keys, params: dict, http=requests.get) -> dict:
    for _ in range(20):
        k = keys.get()
        try:
            j = http(URL, params={**params, "apikey": k}, timeout=60).json()
        except (requests.RequestException, ValueError):
            keys.back_off(k, 5)
            continue
        code = j.get("code")
        if code == 429:                       # per-minute credit limit: this key rests until the minute rolls
            keys.back_off(k, 61)
        elif code in (401, 403):
            keys.back_off(k, 3600)
        elif code == 400 and "no data" in j.get("message", "").lower():
            return {"values": []}
        elif code and code != 200:
            raise RuntimeError(f"twelvedata {code}: {j.get('message')}")
        else:
            return j
    raise RuntimeError("twelvedata: all keys exhausted/backing off")


def fetch_range(keys: Keys, symbol: str, start: str, end: str, prepost: bool, size: int = 5000,
                http=requests.get) -> pd.DataFrame:
    """Bars in [start, end] (ET, 'YYYY-MM-DD HH:MM:SS'), paginated forward by outputsize."""
    out, cur = [], start
    while True:
        j = _request(keys, dict(symbol=symbol, interval="1min", start_date=cur, end_date=end,
                                outputsize=size, timezone=TZ, order="asc", prepost=str(prepost).lower(),
                                format="JSON"), http)
        vals = j.get("values") or []
        if not vals:
            break
        out += vals
        last = vals[-1]["datetime"]
        if len(vals) < size:
            break
        cur = (datetime.fromisoformat(last) + timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")
    if not out:
        return pd.DataFrame(columns=COLS)
    d = pd.DataFrame(out)
    t = pd.to_datetime(d["datetime"]).dt.tz_localize(TZ, ambiguous="NaT", nonexistent="NaT")
    d = pd.DataFrame({"time": t.dt.tz_convert("UTC"), **{c: pd.to_numeric(d[c]) for c in COLS[1:]}})
    return d.dropna(subset=["time"]).drop_duplicates("time").sort_values("time").reset_index(drop=True)


# ---- cache: data/cache/<SYM>/<YYYY-MM>.parquet + coverage.json (days already requested)
def _dir(cfg, sym):
    d = cfg["paths"]["cache"] / sym
    d.mkdir(parents=True, exist_ok=True)
    return d


def _covered(d) -> set[str]:
    f = d / "coverage.json"
    return set(json.loads(f.read_text())) if f.exists() else set()


def _missing_ranges(covered: set[str], start: date, end: date) -> list[tuple[date, date]]:
    rngs, run = [], None
    day = start
    while day <= end:
        if day.weekday() < 5 and day.isoformat() not in covered:
            run = (run[0], day) if run else (day, day)
        elif run and day.weekday() < 5:
            rngs.append(run); run = None
        day += timedelta(days=1)
    if run:
        rngs.append(run)
    return rngs


def _store(d, df: pd.DataFrame) -> None:
    for ym, g in df.groupby(df["time"].dt.tz_convert(TZ).dt.strftime("%Y-%m")):
        f = d / f"{ym}.parquet"
        if f.exists():
            g = pd.concat([pd.read_parquet(f), g]).drop_duplicates("time")
        g.sort_values("time").to_parquet(f, index=False)


def fetch_symbol(cfg, keys: Keys, sym: str, start: str, end: str, http=requests.get) -> tuple[int, int]:
    """Fetch only missing weekdays; returns (new_rows, new_ranges_fetched)."""
    d = _dir(cfg, sym)
    cov = _covered(d)
    last = min(date.fromisoformat(end), date.today() - timedelta(days=1))   # today is incomplete
    prepost = cfg["data"]["extended_hours"]
    rows = n = 0
    for a, b in _missing_ranges(cov, date.fromisoformat(start), last):
        try:
            df = fetch_range(keys, sym, f"{a} 00:00:00", f"{b} 23:59:59", prepost, cfg["data"]["outputsize"], http)
        except RuntimeError as e:
            if prepost and "prepost" in str(e).lower():     # plan has no extended hours -> RTH only
                print(f"{sym}: plan lacks pre/post-market, falling back to RTH only")
                cfg["data"]["extended_hours"] = prepost = False
                df = fetch_range(keys, sym, f"{a} 00:00:00", f"{b} 23:59:59", prepost, cfg["data"]["outputsize"], http)
            else:
                raise
        _store(d, df)
        rows += len(df); n += 1
        day = a
        while day <= b:
            cov.add(day.isoformat()); day += timedelta(days=1)
        (d / "coverage.json").write_text(json.dumps(sorted(cov)))     # per range: resumable
    return rows, n


def summary(cfg, sym: str) -> tuple[int, int]:
    fs = sorted(_dir(cfg, sym).glob("*.parquet"))
    if not fs:
        return 0, 0
    t = pd.concat(pd.read_parquet(f, columns=["time"]) for f in fs)["time"]
    return len(t), t.dt.tz_convert(TZ).dt.date.nunique()


def fetch_many(cfg, symbols: list[str], start: str, end: str, http=requests.get) -> None:
    keys = Keys([k for k in os.environ.get("TWELVEDATA_API_KEYS", "").split(",") if k.strip()])
    if not keys.keys:
        raise SystemExit("TWELVEDATA_API_KEYS missing in .env")
    for s in symbols:
        new, n = fetch_symbol(cfg, keys, s, start, end, http)
        rows, days = summary(cfg, s)
        print(f"{s}: +{new} rows ({n} requests) | cached {rows} rows / {days} days")

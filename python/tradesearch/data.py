"""
Market data: providers + an on-disk cache.

  binance  crypto, public klines endpoint, no key, deep history at every timeframe
  yahoo    stocks / ETFs / forex / futures / indices, public chart endpoint, no key;
           intraday history is limited by Yahoo (1m ≈ 7 days, 5–30m ≈ 60 days, 1h ≈ 730 days)
  twelvedata  stocks / forex / crypto with the user's own key (env TWELVE_DATA_API_KEY or
           TWELVEDATA_API_KEY) — never committed, never logged

Bars are returned as a DataFrame: time (ms, UTC, bar open), open, high, low, close, volume.
TradeSearcher backtests on ~20,000 bars; ``fetch(..., bars=20000)`` asks for that many.
"""

from __future__ import annotations

import os
import time as _time
from dataclasses import dataclass
from pathlib import Path

import httpx
import pandas as pd

CACHE_DIR = Path(os.environ.get("TRADESEARCH_CACHE", Path(__file__).resolve().parents[1] / "data_cache"))
UA = {"User-Agent": "Mozilla/5.0 (tradesearch research backend)"}


@dataclass(frozen=True)
class SymbolRef:
    """A tradable instrument as TradeSearcher names it (EXCHANGE:TICKER) plus how to fetch it."""
    tickerid: str              # e.g. BINANCE:BTCUSDT, NASDAQ:AAPL, FX:EURUSD, CME_MINI:NQ1!
    type: str                  # crypto | stock | forex | futures | index
    provider: str              # binance | yahoo | twelvedata
    provider_symbol: str       # BTCUSDT | AAPL | EURUSD=X | NQ=F
    description: str = ""
    currency: str = "USD"
    base_currency: str = ""

    @property
    def ticker(self) -> str:
        return self.tickerid.split(":")[-1]

    @property
    def exchange(self) -> str:
        return self.tickerid.split(":")[0]


# ─────────────────────────────────────────────────────────────── timeframes
BINANCE_TF = {"1": "1m", "3": "3m", "5": "5m", "15": "15m", "30": "30m", "60": "1h", "120": "2h",
              "240": "4h", "360": "6h", "720": "12h", "D": "1d", "1D": "1d", "W": "1w", "1W": "1w", "M": "1M"}
YAHOO_TF = {"1": ("1m", "7d"), "2": ("2m", "60d"), "5": ("5m", "60d"), "15": ("15m", "60d"),
            "30": ("30m", "60d"), "60": ("60m", "730d"), "D": ("1d", "max"), "1D": ("1d", "max"),
            "W": ("1wk", "max"), "1W": ("1wk", "max"), "M": ("1mo", "max")}
TWELVE_TF = {"1": "1min", "5": "5min", "15": "15min", "30": "30min", "60": "1h", "120": "2h",
             "240": "4h", "D": "1day", "1D": "1day", "W": "1week", "M": "1month"}


def _cache_path(ref: SymbolRef, tf: str) -> Path:
    safe = ref.tickerid.replace(":", "_").replace("!", "")
    return CACHE_DIR / ref.provider / f"{safe}_{tf}.csv"


def load_cached(ref: SymbolRef, tf: str) -> pd.DataFrame | None:
    p = _cache_path(ref, tf)
    if not p.exists():
        return None
    df = pd.read_csv(p)
    return df if len(df) else None


def save_cache(ref: SymbolRef, tf: str, df: pd.DataFrame) -> None:
    p = _cache_path(ref, tf)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False)


def fetch(ref: SymbolRef, tf: str, bars: int = 20_000, refresh: bool = False,
          max_age_hours: float = 12.0) -> pd.DataFrame:
    """Bars for ``ref`` at ``tf`` — from the cache when fresh, else from the provider
    (merged into the cache so history accumulates across runs)."""
    cached = load_cached(ref, tf)
    if cached is not None and not refresh:
        age_h = (_time.time() - _cache_path(ref, tf).stat().st_mtime) / 3600
        if age_h < max_age_hours and len(cached) >= min(bars, 500):
            return cached.tail(bars).reset_index(drop=True)
    fresh = {"binance": _binance, "yahoo": _yahoo, "twelvedata": _twelvedata}[ref.provider](ref, tf, bars)
    if cached is not None and len(cached):
        fresh = pd.concat([cached, fresh]).drop_duplicates("time", keep="last").sort_values("time")
    fresh = fresh.reset_index(drop=True)
    save_cache(ref, tf, fresh)
    return fresh.tail(bars).reset_index(drop=True)


def _frame(rows: list[tuple]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=["time", "open", "high", "low", "close", "volume"])
    df = df.dropna(subset=["open", "high", "low", "close"])
    df["time"] = df["time"].astype("int64")
    return df.drop_duplicates("time").sort_values("time").reset_index(drop=True)


# ─────────────────────────────────────────────────────────────── providers
def _binance(ref: SymbolRef, tf: str, bars: int) -> pd.DataFrame:
    interval = BINANCE_TF[tf]
    rows: list[tuple] = []
    end = None
    with httpx.Client(timeout=30, headers=UA) as c:
        while len(rows) < bars:
            params = {"symbol": ref.provider_symbol, "interval": interval, "limit": 1000}
            if end is not None:
                params["endTime"] = end
            r = c.get("https://api.binance.com/api/v3/klines", params=params)
            r.raise_for_status()
            chunk = r.json()
            if not chunk:
                break
            rows = [(k[0], float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])) for k in chunk] + rows
            end = chunk[0][0] - 1
            if len(chunk) < 1000:
                break
            _time.sleep(0.15)
    return _complete_only(_frame(rows), tf)


def _yahoo(ref: SymbolRef, tf: str, bars: int) -> pd.DataFrame:
    interval, rng = YAHOO_TF[tf]
    params = {"interval": interval, "includePrePost": "false"}
    if rng == "max":
        # range=max silently downgrades daily bars to quarterly; explicit dates keep daily
        params.update(period1=0, period2=int(_time.time()))
    else:
        params["range"] = rng
    with httpx.Client(timeout=30, headers=UA) as c:
        r = c.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{ref.provider_symbol}", params=params)
        r.raise_for_status()
        res = r.json()["chart"]["result"][0]
    ts = res.get("timestamp") or []
    q = res["indicators"]["quote"][0]
    rows = [(t * 1000, q["open"][i], q["high"][i], q["low"][i], q["close"][i], q["volume"][i] or 0.0)
            for i, t in enumerate(ts)]
    return _complete_only(_frame(rows), tf)


def _complete_only(df: pd.DataFrame, tf: str) -> pd.DataFrame:
    """Drop the still-forming last bar (Yahoo returns it with an odd timestamp)."""
    from pinelib import tf_seconds
    if not len(df):
        return df
    secs = tf_seconds(tf)
    now_ms = int(_time.time() * 1000)
    if secs < 86400:
        aligned = (df["time"] // 1000) % 60 == 0
        df = df[aligned]
        if len(df) and df["time"].iloc[-1] + secs * 1000 > now_ms:
            df = df.iloc[:-1]
    elif len(df):
        # daily and higher: the bar of the current UTC day may still be trading
        today = pd.Timestamp(now_ms, unit="ms", tz="UTC").normalize().value // 1_000_000
        if secs == 86400 and df["time"].iloc[-1] >= today:
            df = df.iloc[:-1]
    return df.reset_index(drop=True)


def _twelvedata(ref: SymbolRef, tf: str, bars: int) -> pd.DataFrame:
    key = os.environ.get("TWELVE_DATA_API_KEY") or os.environ.get("TWELVEDATA_API_KEY")
    if not key:
        raise RuntimeError("set TWELVE_DATA_API_KEY to use the twelvedata provider")
    with httpx.Client(timeout=60, headers=UA) as c:
        r = c.get("https://api.twelvedata.com/time_series",
                  params={"symbol": ref.provider_symbol, "interval": TWELVE_TF[tf],
                          "outputsize": min(bars, 5000), "timezone": "UTC", "apikey": key})
        r.raise_for_status()
        body = r.json()
    if body.get("status") == "error":
        raise RuntimeError(f"twelvedata: {body.get('message')}")
    rows = []
    for v in body.get("values", []):
        t = int(pd.Timestamp(v["datetime"], tz="UTC").value // 1_000_000)
        rows.append((t, float(v["open"]), float(v["high"]), float(v["low"]), float(v["close"]),
                     float(v.get("volume") or 0.0)))
    return _frame(rows)


# ─────────────────────────────────────────────────────────────── universe
def _c(t: str, sym: str, desc: str) -> SymbolRef:
    return SymbolRef(f"BINANCE:{t}", "crypto", "binance", sym, desc, "USDT", t[:-4])


def _s(ex: str, t: str, desc: str, kind: str = "stock") -> SymbolRef:
    return SymbolRef(f"{ex}:{t}", kind, "yahoo", t, desc)


DEFAULT_UNIVERSE: list[SymbolRef] = [
    _c("BTCUSDT", "BTCUSDT", "Bitcoin / TetherUS"), _c("ETHUSDT", "ETHUSDT", "Ethereum / TetherUS"),
    _c("SOLUSDT", "SOLUSDT", "SOL / TetherUS"), _c("XRPUSDT", "XRPUSDT", "XRP / TetherUS"),
    _c("BNBUSDT", "BNBUSDT", "Binance Coin / TetherUS"), _c("DOGEUSDT", "DOGEUSDT", "Dogecoin / TetherUS"),
    _c("ADAUSDT", "ADAUSDT", "Cardano / TetherUS"), _c("TRXUSDT", "TRXUSDT", "TRON / TetherUS"),
    _s("NASDAQ", "AAPL", "Apple Inc."), _s("NASDAQ", "MSFT", "Microsoft Corporation"),
    _s("NASDAQ", "NVDA", "NVIDIA Corporation"), _s("NASDAQ", "TSLA", "Tesla, Inc."),
    _s("NASDAQ", "AMZN", "Amazon.com, Inc."), _s("NASDAQ", "META", "Meta Platforms, Inc."),
    _s("NASDAQ", "GOOGL", "Alphabet Inc."), _s("NASDAQ", "AMD", "Advanced Micro Devices"),
    _s("NASDAQ", "MU", "Micron Technology, Inc."), _s("NYSE", "JPM", "JPMorgan Chase & Co."),
    _s("AMEX", "SPY", "SPDR S&P 500 ETF", "stock"), _s("NASDAQ", "QQQ", "Invesco QQQ Trust", "stock"),
    SymbolRef("FX:EURUSD", "forex", "yahoo", "EURUSD=X", "Euro / U.S. Dollar"),
    SymbolRef("FX:GBPUSD", "forex", "yahoo", "GBPUSD=X", "British Pound / U.S. Dollar"),
    SymbolRef("FX:USDJPY", "forex", "yahoo", "JPY=X", "U.S. Dollar / Japanese Yen"),
    SymbolRef("FX:AUDUSD", "forex", "yahoo", "AUDUSD=X", "Australian Dollar / U.S. Dollar"),
    SymbolRef("OANDA:XAUUSD", "forex", "yahoo", "GC=F", "Gold Spot / U.S. Dollar (via COMEX GC)"),
    SymbolRef("CME_MINI:ES1!", "futures", "yahoo", "ES=F", "E-mini S&P 500 Futures"),
    SymbolRef("CME_MINI:NQ1!", "futures", "yahoo", "NQ=F", "E-mini Nasdaq-100 Futures"),
    SymbolRef("NYMEX:CL1!", "futures", "yahoo", "CL=F", "Crude Oil Futures"),
]


# Symbols scripts REQUEST (request.security) but which are not backtested themselves.
AUXILIARY: list[SymbolRef] = [
    SymbolRef("CBOE:VIX", "index", "yahoo", "^VIX", "CBOE Volatility Index"),
    SymbolRef("TVC:VIX", "index", "yahoo", "^VIX", "CBOE Volatility Index"),
    SymbolRef("TVC:DXY", "index", "yahoo", "DX-Y.NYB", "U.S. Dollar Index"),
    SymbolRef("SP:SPX", "index", "yahoo", "^GSPC", "S&P 500 Index"),
    SymbolRef("TVC:SPX", "index", "yahoo", "^GSPC", "S&P 500 Index"),
    SymbolRef("NASDAQ:NDX", "index", "yahoo", "^NDX", "Nasdaq-100 Index"),
    SymbolRef("TVC:US10Y", "index", "yahoo", "^TNX", "U.S. 10-year yield (x10)"),
    SymbolRef("AMEX:SPY", "stock", "yahoo", "SPY", "SPDR S&P 500 ETF"),
    SymbolRef("NASDAQ:QQQ", "stock", "yahoo", "QQQ", "Invesco QQQ Trust"),
    SymbolRef("AMEX:IWM", "stock", "yahoo", "IWM", "iShares Russell 2000 ETF"),
    SymbolRef("BINANCE:BTCUSDT", "crypto", "binance", "BTCUSDT", "Bitcoin / TetherUS"),
]


def find_symbol(query: str, universe: list[SymbolRef] | None = None) -> SymbolRef | None:
    q = query.strip().upper()
    u = (universe or DEFAULT_UNIVERSE) + ([] if universe else AUXILIARY)
    for r in u:
        if r.tickerid.upper() == q:
            return r
    for r in u:
        if r.ticker.upper() == q or r.provider_symbol.upper() == q:
            return r
    return None


def provider_for_scripts(n_bars: int = 20_000):
    """``data_provider(symbol, timeframe)`` for pinelib's request.security on other symbols."""
    def get(symbol: str, tf: str) -> pd.DataFrame:
        ref = find_symbol(symbol)
        if ref is None:
            raise LookupError(f"no data source configured for {symbol!r} (add it to data.AUXILIARY)")
        return fetch(ref, tf, bars=n_bars)
    return get

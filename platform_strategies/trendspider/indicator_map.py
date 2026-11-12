"""
Maps TrendSpider indicator descriptors onto QIS indicators.

Each operand in an extracted TrendSpider strategy names an indicator by
`indicatorType` (e.g. "EMA"), the parameters it was configured with
(`inputs`), and WHICH output series it reads (`outSeries` -- e.g. MACD's
"outMACD" vs "outMACDSignal"). This module turns that triple into a
concrete pandas Series, delegating the math to app.indicators so the
platform's rule holds: strategies compose indicators, they never
reimplement indicator math.

Deliberately explicit rather than clever: a wrong silent mapping (say,
Keltner's band read as Bollinger's) would produce a plausible-looking
backtest that is quietly wrong, which is worse than a loud failure. So
anything not listed here raises UnsupportedIndicator and the strategy
using it is registered as unsupported instead of guessed at.

Naming note: several TrendSpider names differ from the QIS/industry ones
for the same maths -- PRICECHANNELS is Donchian, KELTERCHANNEL (their
typo) is Keltner, ARNAUD_LEGOUX_MA is ALMA, GUPPY_MA is GMMA,
REL_VOLUME is RVOL, LEAST_SQUARES_MOVING_AVERAGE is linear regression.
"""

from __future__ import annotations

from typing import Any, Callable

import pandas as pd

from app.indicators.registry import indicator_registry


class UnsupportedIndicator(Exception):
    """Raised for a TrendSpider indicator with no verified QIS equivalent."""


# TrendSpider `priceSource` -> OHLCV column.
PRICE_SOURCE = {
    "close": "close", "open": "open", "high": "high", "low": "low",
    "hl2": "hl2", "hlc3": "hlc3", "ohlc4": "ohlc4",
}


def _source_series(df: pd.DataFrame, source: str) -> pd.Series:
    """Resolve a price source, synthesising the composite ones."""
    source = (source or "close").lower()
    if source in df.columns:
        return df[source]
    if source == "hl2":
        return (df["high"] + df["low"]) / 2
    if source == "hlc3":
        return (df["high"] + df["low"] + df["close"]) / 3
    if source == "ohlc4":
        return (df["open"] + df["high"] + df["low"] + df["close"]) / 4
    raise UnsupportedIndicator(f"unknown price source {source!r}")


_DISCOVERED = False


def _ensure_indicators_discovered() -> None:
    """Populate the indicator registry.

    Hand-written strategies register indicators implicitly, by importing
    the classes they use. This interpreter resolves indicators by NAME at
    run time, so it can't rely on someone else's import having happened
    first -- without this, perfectly available indicators (sar, willr,
    dema, linearreg...) look "unknown".
    """
    global _DISCOVERED
    if not _DISCOVERED:
        from app.core.registry import discover_package

        discover_package("app.indicators")
        _DISCOVERED = True


def _materialise_source(df: pd.DataFrame, source: str) -> tuple[pd.DataFrame, str]:
    """QIS indicators take a source by COLUMN NAME, but TrendSpider also
    allows composite sources (hl2/hlc3/ohlc4) that aren't columns. Add the
    composite as a real column so the indicator can address it."""
    source = (source or "close").lower()
    if source in df.columns:
        return df, source
    return df.assign(**{source: _source_series(df, source)}), source


def _via_registry(name: str, params: dict[str, Any], pick: Callable[[list[str]], str] | None = None):
    """Run a registered QIS indicator and return the series it produced.

    Column names differ per indicator (ema_20, rsi_14, ...), so rather
    than hardcoding them, take whatever NEW column(s) the indicator added
    and let the caller pick among them when there is more than one.
    """

    def run(df: pd.DataFrame) -> pd.Series:
        _ensure_indicators_discovered()
        if "source" in params:
            df, params["source"] = _materialise_source(df, params["source"])
        indicator = indicator_registry.get(name)()
        before = set(df.columns)
        out = indicator.calculate(df, params)
        added = [c for c in out.columns if c not in before]
        if not added:
            raise UnsupportedIndicator(f"indicator {name!r} produced no new column")
        chosen = pick(added) if pick else added[0]
        return out[chosen]

    return run


def _first_matching(added: list[str], *needles: str) -> str:
    """Pick the added column whose name contains one of `needles`."""
    for needle in needles:
        for col in added:
            if needle in col.lower():
                return col
    return added[0]


def resolve_indicator(definition: dict, df: pd.DataFrame) -> pd.Series:
    """TrendSpider indicator descriptor -> the pandas Series it refers to."""
    ind_type = (definition.get("indicatorType") or "").upper()
    inputs = definition.get("inputs") or {}
    out_series = (definition.get("outSeries") or "").lower()
    period = inputs.get("optInTimePeriod") or inputs.get("length") or inputs.get("period")
    src = inputs.get("priceSource") or inputs.get("price_source") or "close"

    if ind_type in TS_ENGINE_BUILTIN_TYPES:
        ts = _ts_engine_builtin(ind_type, inputs, out_series, period, src, df)
        if ts is not None:
            return ts

    # --- plain moving averages / single-series overlays ------------------
    if ind_type == "EMA":
        return _via_registry("ema", {"period": period, "source": src})(df)
    if ind_type == "SMA":
        return _via_registry("sma", {"period": period, "source": src})(df)
    if ind_type == "DEMA":
        return _via_registry("dema", {"period": period, "source": src})(df)
    if ind_type == "TEMA":
        return _via_registry("tema", {"period": period, "source": src})(df)
    if ind_type == "WMA":
        return _via_registry("wma", {"period": period, "source": src})(df)
    if ind_type == "HMA":
        return _via_registry("hma", {"period": period, "source": src})(df)
    if ind_type == "VWMA":
        return _via_registry("vwma", {"period": period, "source": src})(df)
    if ind_type == "KAMA":
        return _via_registry("kama", {"period": period, "source": src})(df)
    if ind_type == "ZLEMA":
        return _via_registry("zlema", {"period": period, "source": src})(df)
    if ind_type == "VIDYA":
        return _via_registry("vidya", {"period": period, "source": src})(df)
    if ind_type == "TRIMA":
        return _via_registry("trima", {"period": period, "source": src})(df)
    if ind_type == "ARNAUD_LEGOUX_MA":  # ALMA
        return _via_registry(
            "alma",
            {"period": inputs.get("window") or period, "offset": inputs.get("offs", 0.85),
             "sigma": inputs.get("sigma", 6), "source": src},
        )(df)
    if ind_type == "SMOOTHED_MOVING_AVERAGE":
        # SMMA/RMA: an EMA with alpha = 1/period (Wilder's smoothing).
        return _source_series(df, src).ewm(alpha=1.0 / float(period), adjust=False,
                                           min_periods=int(period)).mean()
    if ind_type == "LEAST_SQUARES_MOVING_AVERAGE":
        return _via_registry("linearreg", {"period": period, "source": src})(df)

    # --- price/volume -----------------------------------------------------
    if ind_type == "VOLUME":
        vol = df["volume"]
        if out_series in ("sma", "ma"):
            return vol.rolling(int(period), min_periods=int(period)).mean()
        return vol
    if ind_type == "REL_VOLUME":  # RVOL
        return _via_registry("rvol", {"period": period or 20})(df)
    if ind_type == "VWAP":
        return _via_registry("vwap", {})(df)
    if ind_type == "OBV":
        return _via_registry("obv", {})(df)
    if ind_type == "TWAP":
        # Time-weighted average price: the running mean of typical price
        # over the session, the time-weighted counterpart to VWAP.
        typical = (df["high"] + df["low"] + df["close"]) / 3
        if isinstance(df.index, pd.DatetimeIndex):
            return typical.groupby(df.index.date).expanding().mean().reset_index(level=0, drop=True)
        return typical.expanding().mean()

    # --- oscillators ------------------------------------------------------
    if ind_type == "RSI":
        return _via_registry("rsi", {"period": period, "source": src})(df)
    if ind_type == "CCI":
        return _via_registry("cci", {"period": period})(df)
    if ind_type == "WILLR":
        return _via_registry("willr", {"period": period})(df)
    if ind_type == "MFI":
        return _via_registry("mfi", {"period": period})(df)
    if ind_type == "ROC":
        return _via_registry("roc", {"period": period, "source": src})(df)
    if ind_type == "ADX":
        return _via_registry("adx", {"period": period})(df)
    if ind_type == "ATR":
        return _via_registry("atr", {"period": period})(df)
    if ind_type == "STDDEV":
        return _source_series(df, src).rolling(int(period), min_periods=int(period)).std(ddof=0)

    if ind_type == "MACD":
        params = {
            "fast_period": inputs.get("optInFastPeriod", 12),
            "slow_period": inputs.get("optInSlowPeriod", 26),
            "signal_period": inputs.get("optInSignalPeriod", 9),
            "source": src,
        }
        picker = {
            "outmacd": lambda cols: _first_matching(cols, "macd_line", "macd"),
            "outmacdsignal": lambda cols: _first_matching(cols, "signal"),
            "outmacdhist": lambda cols: _first_matching(cols, "hist"),
        }.get(out_series)
        return _via_registry("macd", params, picker)(df)

    if ind_type == "STOCH":
        params = {
            "k_period": inputs.get("optInFastK_Period", 14),
            "d_period": inputs.get("optInSlowD_Period", 3),
        }
        picker = (lambda cols: _first_matching(cols, "_d", "slowd")) if out_series.endswith("d") \
            else (lambda cols: _first_matching(cols, "_k", "slowk"))
        return _via_registry("stoch", params, picker)(df)

    # --- bands / channels -------------------------------------------------
    if ind_type == "BBANDS":
        params = {
            "period": inputs.get("optInTimePeriod", 20),
            "std_dev": inputs.get("optInNbDevUp", 2),
            "source": src,
        }
        picker = {
            "outrealupperband": lambda cols: _first_matching(cols, "upper"),
            "outreallowerband": lambda cols: _first_matching(cols, "lower"),
            "outrealmiddleband": lambda cols: _first_matching(cols, "middle", "mid"),
        }.get(out_series, lambda cols: _first_matching(cols, "middle", "mid"))
        return _via_registry("bbands", params, picker)(df)

    if ind_type == "PRICECHANNELS":  # TrendSpider's name for Donchian
        params = {"period": inputs.get("length", 20)}
        picker = {
            "high": lambda cols: _first_matching(cols, "upper", "high"),
            "low": lambda cols: _first_matching(cols, "lower", "low"),
            "middle": lambda cols: _first_matching(cols, "middle", "mid"),
        }.get(out_series, lambda cols: _first_matching(cols, "middle", "mid"))
        return _via_registry("donchian", params, picker)(df)

    if ind_type == "KELTERCHANNEL":  # their spelling of Keltner
        params = {
            "period": inputs.get("length", 20),
            "atr_period": inputs.get("atrLength", 10),
            "multiplier": inputs.get("multiplier", 2),
        }
        picker = {
            "high": lambda cols: _first_matching(cols, "upper", "high"),
            "low": lambda cols: _first_matching(cols, "lower", "low"),
            "middle": lambda cols: _first_matching(cols, "middle", "mid"),
        }.get(out_series, lambda cols: _first_matching(cols, "middle", "mid"))
        return _via_registry("keltner", params, picker)(df)

    if ind_type == "SUPERTREND":
        params = {"period": inputs.get("atrLength", 10), "multiplier": inputs.get("multiplier", 3)}
        return _via_registry("supertrend", params)(df)

    if ind_type == "SAR":
        params = {
            "acceleration": inputs.get("optInAcceleration", 0.02),
            "maximum": inputs.get("optInMaximum", 0.2),
        }
        return _via_registry("sar", params)(df)

    if ind_type == "GUPPY_MA":  # GMMA
        # GMMA is twelve EMAs; the model names which one via outSeries
        # ("fast_1".."fast_6", "slow_1".."slow_6") and carries that line's
        # period in its inputs. Returning the registry's first column
        # would silently use the wrong EMA for every condition.
        line_period = inputs.get(out_series)
        if line_period is None:
            raise UnsupportedIndicator(f"GUPPY_MA line {out_series!r} has no period in inputs")
        return _via_registry("ema", {"period": int(line_period), "source": src})(df)

    if ind_type == "MOM":
        return _via_registry("mom", {"period": period, "source": src})(df)
    if ind_type == "HT_TRENDLINE":
        return _via_registry("ht_trendline", {})(df)
    if ind_type == "MAMA":
        params = {
            "fast_limit": inputs.get("optInFastLimit", 0.5),
            "slow_limit": inputs.get("optInSlowLimit", 0.05),
        }
        picker = (lambda cols: _first_matching(cols, "fama")) if "fama" in out_series \
            else (lambda cols: _first_matching(cols, "mama"))
        return _via_registry("mama", params, picker)(df)

    if ind_type == "ICHIMOKU":
        params = {
            "conversion_period": inputs.get("tenkanSenLength", 9),
            "base_period": inputs.get("kijunSenLength", 26),
            "leading_span_b_period": inputs.get("senkouSpanBLength", 52),
        }
        picker = {
            "tenkansen": lambda cols: _first_matching(cols, "conversion", "tenkan"),
            "kijunsen": lambda cols: _first_matching(cols, "base", "kijun"),
            "senkouspana": lambda cols: _first_matching(cols, "span_a", "spana", "senkou_a"),
            "senkouspanb": lambda cols: _first_matching(cols, "span_b", "spanb", "senkou_b"),
            "chikouspan": lambda cols: _first_matching(cols, "chikou", "lagging"),
        }.get(out_series)
        if picker is None:
            raise UnsupportedIndicator(f"ICHIMOKU output {out_series!r} not mapped")
        return _via_registry("ichimoku", params, picker)(df)

    if ind_type == "TODAYOPEN":
        return _via_registry("session_open_price", {})(df)

    if ind_type == "TIME":
        # Genuinely calendar-anchored: stays wall-clock/date regardless of
        # the bar interval, exactly as TrendSpider treats it. `outSeries`
        # picks WHICH unit is being compared -- returning minutes-since-
        # midnight for a "month of year" comparison silently makes the
        # condition permanently false (it's what made "Sell In May" fire
        # zero times).
        if not isinstance(df.index, pd.DatetimeIndex):
            raise UnsupportedIndicator("TIME requires a DatetimeIndex")
        if out_series == "monthofyear":
            return pd.Series(df.index.month, index=df.index, dtype=float)
        if out_series == "hoursminutes":
            # TrendSpider compares this against an HHMM number (e.g. 0930).
            return pd.Series(df.index.hour * 100 + df.index.minute, index=df.index, dtype=float)
        if out_series == "dayofweek":
            return pd.Series(df.index.dayofweek + 1, index=df.index, dtype=float)
        if out_series == "dayofmonth":
            return pd.Series(df.index.day, index=df.index, dtype=float)
        raise UnsupportedIndicator(f"TIME unit {out_series!r} not mapped")

    if ind_type == "VORTEX":
        # VI+ / VI-: directional movement normalised by true range.
        n = int(period or 14)
        prev_close = df["close"].shift(1)
        true_range = pd.concat(
            [df["high"] - df["low"], (df["high"] - prev_close).abs(),
             (df["low"] - prev_close).abs()], axis=1,
        ).max(axis=1)
        vm_plus = (df["high"] - df["low"].shift(1)).abs()
        vm_minus = (df["low"] - df["high"].shift(1)).abs()
        tr_sum = true_range.rolling(n, min_periods=n).sum()
        if out_series in ("negative", "vi_minus", "minus"):
            return vm_minus.rolling(n, min_periods=n).sum() / tr_sum
        return vm_plus.rolling(n, min_periods=n).sum() / tr_sum

    if ind_type in ("TDI", "RSI_WITH_VOL_BANDS"):
        # Both are "RSI plus Bollinger Bands computed ON the RSI".
        # TDI adds two smoothings of the RSI (fast/slow signal lines).
        rsi = _via_registry("rsi", {"period": inputs.get("optInTimePeriod", 14), "source": src})(df)
        bb_len = int(inputs.get("bbLength", 34 if ind_type == "TDI" else 20))
        dev_up = float(inputs.get("bbDevUp", 1.618 if ind_type == "TDI" else 2))
        dev_dn = float(inputs.get("bbDevDn", dev_up))
        mid = rsi.rolling(bb_len, min_periods=bb_len).mean()
        sd = rsi.rolling(bb_len, min_periods=bb_len).std(ddof=0)
        if out_series in ("bbup", "bbupper"):
            return mid + dev_up * sd
        if out_series in ("bblow", "bblower"):
            return mid - dev_dn * sd
        if out_series in ("bbmiddle", "bbmid"):
            return mid
        if out_series == "mafast":
            return rsi.rolling(int(inputs.get("maFastLength", 2)), min_periods=1).mean()
        if out_series == "maslow":
            return rsi.rolling(int(inputs.get("maSlowLength", 7)), min_periods=1).mean()
        if out_series == "rsi":
            return rsi
        raise UnsupportedIndicator(f"{ind_type} output {out_series!r} not mapped")

    if ind_type == "MA_CLOUD":
        # Two moving averages of the same type; the "cloud" is the gap.
        ma_type = str(inputs.get("maType", "EMA")).lower()
        length = inputs.get("maLength1" if out_series == "ma1" else "maLength2", 20)
        registry_name = {"ema": "ema", "sma": "sma", "wma": "wma", "hma": "hma"}.get(ma_type)
        if not registry_name:
            raise UnsupportedIndicator(f"MA_CLOUD maType {ma_type!r} not mapped")
        return _via_registry(registry_name, {"period": length, "source": src})(df)

    if ind_type == "RANGE":
        # Rolling highest-high / lowest-low over `length` bars.
        n = int(inputs.get("length", 20))
        if out_series == "high":
            return df["high"].rolling(n, min_periods=n).max()
        if out_series == "low":
            return df["low"].rolling(n, min_periods=n).min()
        raise UnsupportedIndicator(f"RANGE output {out_series!r} not mapped")

    if ind_type == "TODAYOPENINGRANGE":
        # "1st Cdl Range": the FIRST bar of each session, held for the
        # rest of that session (TrendSpider's "ladder" interpolation).
        if not isinstance(df.index, pd.DatetimeIndex):
            raise UnsupportedIndicator("TODAYOPENINGRANGE requires a DatetimeIndex")
        session = df.index.date
        column = "high" if out_series == "high" else "low"
        first_of_session = df.groupby(session)[column].transform("first")
        return first_of_session

    if ind_type == "OBV_ANCHORED":
        # OBV restarted at each anchor period (here: week to date).
        direction = df["close"].diff().pipe(lambda s: s.where(s == 0, s.apply(lambda v: 1 if v > 0 else -1)))
        signed_volume = df["volume"] * direction.fillna(0)
        if not isinstance(df.index, pd.DatetimeIndex):
            raise UnsupportedIndicator("OBV_ANCHORED requires a DatetimeIndex")
        anchoring = str(inputs.get("anchoring_type", "week to date")).lower()
        if "week" in anchoring:
            group = df.index.to_period("W")
        elif "month" in anchoring:
            group = df.index.to_period("M")
        elif "day" in anchoring or "session" in anchoring:
            group = pd.Index(df.index.date)
        else:
            raise UnsupportedIndicator(f"OBV anchoring {anchoring!r} not mapped")
        return signed_volume.groupby(group).cumsum()

    # --- custom TrendSpider scripts ---------------------------------------
    # Their source is not in the exported model, but three of the four are
    # fully determined by their title + parameters, so they are
    # reimplemented from the published definitions rather than guessed at.
    if ind_type.startswith("SCRIPT-"):
        return _resolve_script_indicator(definition, df)

    raise UnsupportedIndicator(
        f"no verified QIS mapping for TrendSpider indicator {ind_type!r} "
        f"(outSeries={out_series!r})"
    )


# Built-in indicators computed with TrendSpider's own scripting-engine math
# (sma/stdev/... as ported in app.indicators.trendspider_store._runtime).
# Only where it was measured to reproduce TrendSpider's chart indicators
# better (scripts/trendspider_parity.py --ts-bars, AAPL daily, vs
# TrendSpider's recorded backtests): Bollinger Bands (population stdev).
# The chart's EMA-family built-ins do NOT match the scripting engine's
# first-value-seeded ema() -- 8/21 EMA went from TrendSpider's exact 60
# trades to 61 -- so EMA/DEMA/TEMA/MACD/RSI keep the conventional QIS math.
TS_ENGINE_BUILTIN_TYPES = frozenset(
    t for t in __import__("os").environ.get("TS_ENGINE_BUILTINS", "BBANDS").upper().split(",") if t
)
TS_ENGINE_BUILTINS = bool(TS_ENGINE_BUILTIN_TYPES)

_TS_API_CACHE: dict = {}


def _ts_api(df: pd.DataFrame):
    from app.indicators.trendspider_store._runtime.api import ScriptContext, ScriptResult, make_globals
    from app.indicators.trendspider_store._runtime.indicator import frame_to_bars, infer_resolution

    key = (id(df), len(df), df.index[-1] if len(df) else None)
    if _TS_API_CACHE.get("key") != key:
        res = infer_resolution(df.index)
        bars = frame_to_bars(df, res)
        g = make_globals(ScriptContext(bars, resolution=res, ticker=df.attrs.get("symbol") or "CHART"), ScriptResult())
        _TS_API_CACHE.clear()
        _TS_API_CACHE.update(key=key, g=g)
    return _TS_API_CACHE["g"]


def _ts_engine_builtin(ind_type, inputs, out_series, period, src, df):
    """Series for a built-in TrendSpider indicator via TrendSpider's engine
    math, or None when this indicator isn't expressible with it."""
    g = _ts_api(df)

    def source(name):
        name = str(name or "close").lower()
        prices = g["prices"]
        return prices[name] if name in prices else None

    def out(values):
        return pd.Series([float("nan") if v is None or v is J.undefined else float(v) for v in values],
                         index=df.index, dtype=float)

    from app.indicators.trendspider_store._runtime import js as J

    s = source(src)
    if s is None:
        return None
    n = int(period) if period else None
    simple = {"EMA": "ema", "SMA": "sma", "WMA": "wma", "VWMA": "vwma", "HMA": "hullma"}
    if ind_type in simple and n:
        return out(g[simple[ind_type]](s, n))
    if ind_type == "SMOOTHED_MOVING_AVERAGE" and n:
        return out(g["wildma"](s, n))
    if ind_type == "RSI" and n:
        return out(g["rsi"](s, n))
    if ind_type == "DEMA" and n:
        e1 = g["ema"](s, n)
        return out(g["sub"](g["mult"](e1, 2), g["ema"](e1, n)))
    if ind_type == "TEMA" and n:
        return out(g["indicators"]["tema"](s, n))
    if ind_type == "MACD":
        fast = int(inputs.get("optInFastPeriod", 12))
        slow = int(inputs.get("optInSlowPeriod", 26))
        sig = int(inputs.get("optInSignalPeriod", 9))
        macd = g["sub"](g["ema"](s, fast), g["ema"](s, slow))
        signal = g["ema"](macd, sig)
        if out_series == "outmacd":
            return out(macd)
        if out_series == "outmacdsignal":
            return out(signal)
        if out_series == "outmacdhist":
            return out(g["sub"](macd, signal))
        return None
    if ind_type == "BBANDS":
        n = int(inputs.get("optInTimePeriod", 20))
        up = float(inputs.get("optInNbDevUp", 2))
        dn = float(inputs.get("optInNbDevDn", up))
        mid = g["sma"](s, n)
        dev = g["stdev"](s, n)
        if out_series == "outrealupperband":
            return out(g["add"](mid, g["mult"](dev, up)))
        if out_series == "outreallowerband":
            return out(g["sub"](mid, g["mult"](dev, dn)))
        return out(mid)
    return None


# (title prefix in the strategy model, registered *_TS indicator)
_TS_SCRIPT_INDICATORS = (
    ("ORB Trading Strategy Indicator", "orb_trading_strategy_indicator_TS"),
    ("Golden/Death Cross Painter", "golden_death_cross_painter_TS"),
    ("Weinstein Stage Analysis", "weinstein_stage_analysis_TS"),
    ("Turtle Trading Strategy", "turtle_trading_strategy_long_only_TS"),
    ("Breakout & Fakeout Coloring", "breakout_fakeout_candle_coloring_TS"),
)

_TS_CACHE: dict = {}


def _ts_script_output(ts_name: str, inputs: dict, out_series: str, df: pd.DataFrame) -> pd.Series:
    """One output series of a *_TS indicator. The script runs once per
    (frame, inputs) and every operand the strategy reads from it is served
    from that run -- a strategy typically reads 3-6 outputs of one script."""
    _ensure_indicators_discovered()
    key = (ts_name, id(df), len(df), df.index[-1] if len(df) else None, repr(sorted((inputs or {}).items())))
    if key not in _TS_CACHE:
        if len(_TS_CACHE) > 32:
            _TS_CACHE.clear()
        indicator = indicator_registry.get(ts_name)()
        known = {i["id"] for i in indicator.TS_INPUTS} | {"warmup"}
        params = {k: v for k, v in (inputs or {}).items() if k in known or not indicator.TS_INPUTS}
        _TS_CACHE[key] = indicator.calculate(df, params)
    column = f"{ts_name}__{out_series}"
    frame = _TS_CACHE[key]
    if column not in frame:
        raise UnsupportedIndicator(f"{ts_name} has no output {out_series!r}")
    series = frame[column]
    return series.astype(float) if series.dtype == bool else series


def _resolve_script_indicator(definition: dict, df: pd.DataFrame) -> pd.Series:
    """Custom TrendSpider script indicators, keyed by title.

    The `indicatorType` is a per-subscription hash (script-9cca0113...),
    so it can't be matched on; the human title is the stable identity.
    """
    title = (definition.get("titleShort") or definition.get("title") or "")
    inputs = definition.get("inputs") or {}
    out_series = (definition.get("outSeries") or "").lower()

    # TrendSpider store scripts: computed by the exact *_TS translations
    # (app/indicators/trendspider_store, verified against TrendSpider's own
    # engine). The strategy model carries the script's input values under
    # the same ids the script declares, so they pass straight through.
    for prefix, ts_name in _TS_SCRIPT_INDICATORS:
        if title.startswith(prefix):
            return _ts_script_output(ts_name, inputs, out_series, df)

    # Williams Vix Fix (Chris Moody's published formulation).
    if "WVF" in title:
        pd_len = int(inputs.get("pd", 22))
        bbl = int(inputs.get("bbl", 20))
        mult = float(inputs.get("m", 2))
        lb = int(inputs.get("lb", 50))
        ph = float(inputs.get("ph", 0.85))
        highest_close = df["close"].rolling(pd_len, min_periods=pd_len).max()
        wvf = ((highest_close - df["low"]) / highest_close) * 100
        upper_band = wvf.rolling(bbl, min_periods=bbl).mean() + mult * wvf.rolling(bbl, min_periods=bbl).std(ddof=0)
        range_high = wvf.rolling(lb, min_periods=lb).max() * ph
        if out_series in ("entry__long", "entry_long", "entry"):
            # A volatility spike through either band marks the capitulation
            # low this strategy buys.
            return ((wvf >= upper_band) | (wvf >= range_high)).astype(float)
        if out_series in ("wvf", "outreal"):
            return wvf
        raise UnsupportedIndicator(f"WVF output {out_series!r} not mapped")

    raise UnsupportedIndicator(
        f"custom TrendSpider script {title!r} has no published definition to port "
        f"from; its source is not included in the exported model"
    )

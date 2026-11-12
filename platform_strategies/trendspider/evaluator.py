"""
Evaluates an extracted TrendSpider condition tree against OHLCV bars.

A TrendSpider strategy is a tree, not a flat list:

    enterCondition
      └─ conditions: [ {type: "script", script: BLOCK} ]

    BLOCK = { logicCondition: and|or|none_of,
              conditions: [CONDITION...],      # leaves
              subBlocks:  [BLOCK...],          # nested groups
              useRange, withinRange }          # "happened within N bars"

    CONDITION = { operands: [OPERAND, OPERAND?], operator: {...} }

This module turns that into a boolean Series aligned to the bars. It is
the one place that understands TrendSpider's semantics; everything else
(strategy registration, execution) is ordinary QIS machinery.

Two semantics worth spelling out, because getting either wrong changes
results silently:

* `offset` on an operand means "N candles ago", so it becomes shift(N).
  It is NOT a lookahead -- shifting forward would peek at the future.
* `withinRange` on a block means the block's verdict counts if it was
  true at ANY point in the last N bars, not only on this bar. Applied as
  a backward-looking rolling any(), again never forward.
"""

from __future__ import annotations

import pandas as pd

from app.strategies.trendspider.indicator_map import (
    UnsupportedIndicator,
    resolve_indicator,
    _source_series,
)


class UnsupportedCondition(Exception):
    """A condition this evaluator cannot faithfully reproduce."""


# TA-Lib style candle pattern ids -> a pandas implementation. Only
# patterns implemented exactly are listed; anything else raises rather
# than silently approximating a different pattern.
def _bullish(df: pd.DataFrame) -> pd.Series:
    return df["close"] > df["open"]


def _body(df: pd.DataFrame) -> pd.Series:
    return (df["close"] - df["open"]).abs()


def _range(df: pd.DataFrame) -> pd.Series:
    return (df["high"] - df["low"]).replace(0, float("nan"))


def _upper_wick(df: pd.DataFrame) -> pd.Series:
    return df["high"] - df[["open", "close"]].max(axis=1)


def _lower_wick(df: pd.DataFrame) -> pd.Series:
    return df[["open", "close"]].min(axis=1) - df["low"]


def _cdl_hammer(df, title=""):
    """Long lower wick, small body at the top. TA-Lib separates Hammer
    (bottom reversal) from Hanging Man (top reversal) purely by the
    preceding trend, so that context is applied here too."""
    shape = (_lower_wick(df) >= 2 * _body(df)) & (_upper_wick(df) <= _body(df)) &             ((_body(df) / _range(df)) < 0.35)
    if "hanging" in title.lower():
        uptrend = df["close"] > df["close"].rolling(10, min_periods=10).mean()
        return (shape & uptrend).fillna(False)
    return shape.fillna(False)


def _cdl_inverted_hammer(df, title=""):
    return ((_upper_wick(df) >= 2 * _body(df)) & (_lower_wick(df) <= _body(df)) &
            ((_body(df) / _range(df)) < 0.35)).fillna(False)


def _cdl_doji(df, title=""):
    return ((_body(df) / _range(df)) < 0.1).fillna(False)


def _cdl_dragonfly_doji(df, title=""):
    """Doji with open/close at the TOP: long lower wick, no upper wick."""
    return (((_body(df) / _range(df)) < 0.1) & (_upper_wick(df) <= _range(df) * 0.1) &
            (_lower_wick(df) >= _range(df) * 0.6)).fillna(False)


def _cdl_gravestone_doji(df, title=""):
    """Doji with open/close at the BOTTOM: long upper wick, no lower wick."""
    return (((_body(df) / _range(df)) < 0.1) & (_lower_wick(df) <= _range(df) * 0.1) &
            (_upper_wick(df) >= _range(df) * 0.6)).fillna(False)


def _cdl_engulfing(df, title=""):
    """This bar's body fully engulfs the previous, opposite-coloured one."""
    prev_open, prev_close = df["open"].shift(1), df["close"].shift(1)
    bull = _bullish(df) & (prev_close < prev_open) &            (df["close"] >= prev_open) & (df["open"] <= prev_close)
    bear = ~_bullish(df) & (prev_close > prev_open) &            (df["close"] <= prev_open) & (df["open"] >= prev_close)
    return _pick_direction(bull, bear, title)


def _cdl_harami(df, title=""):
    """The inverse of engulfing: a small body contained inside the
    previous, larger, opposite-coloured body."""
    prev_open, prev_close = df["open"].shift(1), df["close"].shift(1)
    inside = (df[["open", "close"]].max(axis=1) <= pd.concat([prev_open, prev_close], axis=1).max(axis=1)) &              (df[["open", "close"]].min(axis=1) >= pd.concat([prev_open, prev_close], axis=1).min(axis=1))
    bull = inside & _bullish(df) & (prev_close < prev_open)
    bear = inside & ~_bullish(df) & (prev_close > prev_open)
    return _pick_direction(bull, bear, title)


def _cdl_inside_bar(df, title=""):
    """TheStrat "1" bar: this bar's range sits inside the previous bar's."""
    return ((df["high"] <= df["high"].shift(1)) & (df["low"] >= df["low"].shift(1))).fillna(False)


def _cdl_kicker(df, title=""):
    """An opposite-coloured candle gapping away from the previous one."""
    prev_open, prev_close = df["open"].shift(1), df["close"].shift(1)
    bull = (prev_close < prev_open) & _bullish(df) & (df["open"] >= prev_open)
    bear = (prev_close > prev_open) & ~_bullish(df) & (df["open"] <= prev_open)
    return _pick_direction(bull, bear, title)


def _cdl_tweezer(df, title=""):
    """Two consecutive bars sharing almost the same high (top) or low
    (bottom), within a tenth of the bar's range."""
    tolerance = _range(df) * 0.1
    top = ((df["high"] - df["high"].shift(1)).abs() <= tolerance).fillna(False)
    bottom = ((df["low"] - df["low"].shift(1)).abs() <= tolerance).fillna(False)
    return _pick_direction(bottom, top, title, bull_word="bottom", bear_word="top")


def _pick_direction(bullish_side, bearish_side, title, bull_word="bull", bear_word="bear"):
    """TrendSpider stores direction in the pattern's TITLE while reusing
    one id ("Engulfing Bullish" and "Engulfing Bearish" are both
    CDLENGULFING). Returning both directions would roughly double the
    signals, so honour the title when it names one.
    """
    lowered = (title or "").lower()
    if bull_word in lowered:
        return bullish_side.fillna(False)
    if bear_word in lowered:
        return bearish_side.fillna(False)
    return (bullish_side | bearish_side).fillna(False)


CANDLE_PATTERNS = {
    "CDLHAMMER": _cdl_hammer,
    "CDLHANGINGMAN": _cdl_hammer,          # same shape, trend context differs
    "CDLINVERTEDHAMMER": _cdl_inverted_hammer,
    "CDLDOJI": _cdl_doji,
    "CDLDRAGONFLYDOJI": _cdl_dragonfly_doji,
    "CDLGRAVESTONEDOJI": _cdl_gravestone_doji,
    "CDLENGULFING": _cdl_engulfing,
    "CDLHARAMI": _cdl_harami,
    "CDL_R_1": _cdl_inside_bar,
    "CDL_KICKER": _cdl_kicker,
    "CDL_TWEEZER": _cdl_tweezer,
}


def _operand_series(operand: dict, df: pd.DataFrame) -> pd.Series | float:
    """One operand -> a Series (or a scalar for constants)."""
    kind = operand.get("type")
    definition = operand.get("definition") or {}

    if kind == "constant":
        return float(definition.get("value"))

    if kind == "margin":
        # Only meaningful as the tolerance of a market_* operator; the
        # operator handler reads it directly.
        return float(definition.get("value"))

    if kind == "candles":
        # Bare price: definition.outSeries is open/high/low/close.
        series = _source_series(df, definition.get("outSeries") or "close")
    elif kind == "indicator":
        series = resolve_indicator(definition, df)
    elif kind == "candle_pattern":
        pattern_id = (definition.get("id") or "").upper()
        if pattern_id not in CANDLE_PATTERNS:
            raise UnsupportedCondition(f"candle pattern {pattern_id!r} not implemented")
        series = CANDLE_PATTERNS[pattern_id](df, definition.get("title") or "").astype(float)
    else:
        raise UnsupportedCondition(f"operand type {kind!r} not supported")

    # "N candles ago" -> look back N bars. Never negative: that would
    # read the future.
    offset = int(definition.get("offset") or 0)
    if offset:
        series = series.shift(offset)
    return series


_MARKET_OPERATORS = ("market_breakthrough", "market_bounce", "market_touch")


def _market_operator(operator: str, comparands: list[dict], df: pd.DataFrame, margin: float) -> pd.Series:
    """TrendSpider's market_* operators ask about PRICE versus a LEVEL.

    The single named operand is the level (a Bollinger band, a Donchian
    edge, a moving average...) and price is implicit -- which is why
    "Bband breakdown" reads as market_breakthrough(BBANDS lower) and
    "Donchian Channel Long" as market_bounce(Donchian low). Reading the
    operand as one side of an ordinary comparison against the constant
    instead makes every one of these conditions permanently false.
    """
    level = _operand_series(comparands[0], df)
    price = df["close"]
    band_low, band_high = level * (1 - margin), level * (1 + margin)

    if operator == "market_breakthrough":
        # Crossed clean through the level, from either side.
        return _crossed(price, level, up=True) | _crossed(price, level, up=False)

    # Use the bar's RANGE, not just its close: with the margin at 0% (which
    # is what these strategies carry) a close-only band has zero width and
    # essentially never registers a touch -- that is why the Donchian
    # bounce strategies produced 2 trades against TrendSpider's 143.
    reached_low = df["low"] <= band_high
    reached_high = df["high"] >= band_low

    if operator == "market_touch":
        return (reached_low & reached_high).fillna(False)

    # Bounce: the bar reached the level but closed back away from it --
    # rejection off support (or off resistance), decided by which side of
    # the level price generally sits on.
    if _level_is_support(price, level):
        return (reached_low & (price > band_high)).fillna(False)
    return (reached_high & (price < band_low)).fillna(False)


def _level_is_support(price: pd.Series, level: pd.Series) -> bool:
    """Is this level generally BELOW price (support) or above (resistance)?
    Decides which way a 'bounce' should be turning."""
    diff = (price - level).dropna()
    return bool((diff > 0).mean() >= 0.5) if len(diff) else True


def _crossed(a: pd.Series, b, *, up: bool) -> pd.Series:
    prev_a, prev_b = a.shift(1), (b.shift(1) if isinstance(b, pd.Series) else b)
    if up:
        return (a > b) & (prev_a <= prev_b)
    return (a < b) & (prev_a >= prev_b)


def _evaluate_condition(condition: dict, df: pd.DataFrame) -> pd.Series:
    # TrendSpider writes an unset second operand as a literal null inside
    # the operands array, so drop empties rather than indexing into None.
    operands = [o for o in (condition.get("operands") or []) if isinstance(o, dict)]
    op_meta = condition.get("operator") or {}
    operator = op_meta.get("operator") or op_meta.get("type")

    if not operands:
        raise UnsupportedCondition("condition has no operands")

    # A trailing `margin` operand widens the comparison by a percentage
    # ("A is greater than B by 10%"). It is a modifier, not a comparand,
    # so pull it out before pairing up the real operands -- treating it
    # as operand[1] silently compares against the wrong thing.
    margin_pct = 0.0
    comparands = []
    for operand in operands:
        if operand.get("type") == "margin":
            margin_pct = float((operand.get("definition") or {}).get("value", 0)) / 100.0
        elif operand.get("type") == "constant" and operator in _MARKET_OPERATORS:
            # For the market_* operators the constant IS the margin.
            margin_pct = float((operand.get("definition") or {}).get("value", 0)) / 100.0
        else:
            comparands.append(operand)

    if operator in _MARKET_OPERATORS:
        return _market_operator(operator, comparands, df, margin_pct)

    left = _operand_series(comparands[0], df)
    right = _operand_series(comparands[1], df) if len(comparands) > 1 else None
    if right is not None and margin_pct:
        right = right * (1 + margin_pct)

    # A truthiness test on a signal series (e.g. a pattern painter).
    if operator == "series_value_is_truthy":
        return left.astype(bool) if isinstance(left, pd.Series) else pd.Series(bool(left), index=df.index)
    if operator == "series_value_became_truthy":
        as_bool = left.astype(bool)
        return as_bool & ~as_bool.shift(1).fillna(False)

    if operator == "candle_pattern":
        # The pattern operand itself carries the verdict.
        series = left if isinstance(left, pd.Series) else right
        return series.astype(bool)

    if operator == "changed_up":
        return left > left.shift(1)
    if operator == "changed_down":
        return left < left.shift(1)

    if right is None:
        raise UnsupportedCondition(f"operator {operator!r} needs a second operand")

    if operator == "greater_than":
        return left > right
    if operator == "less_than":
        return left < right
    if operator == "greater_or_equal":
        return left >= right
    if operator == "less_or_equal":
        return left <= right
    if operator == "equal":
        return left == right
    if operator == "crosses_up":
        return _crossed(left, right, up=True)
    if operator == "crosses_down":
        return _crossed(left, right, up=False)

    if operator == "within_range":
        # "left is within X% of right", where X comes from a margin
        # operand; with no margin it degenerates to equality.
        margin = 0.0
        for operand in operands[2:]:
            if operand.get("type") == "margin":
                margin = float((operand.get("definition") or {}).get("value", 0)) / 100.0
        return (left >= right * (1 - margin)) & (left <= right * (1 + margin))

    if operator == "within_range":
        # "left is within X% of right", where X comes from a margin
        # operand; with no margin it degenerates to equality.
        margin = 0.0
        for operand in operands[2:]:
            if operand.get("type") == "margin":
                margin = float((operand.get("definition") or {}).get("value", 0)) / 100.0
        return (left >= right * (1 - margin)) & (left <= right * (1 + margin))

    # market_* operators compare against a level with a margin operand.
    if operator in ("market_breakthrough", "market_bounce", "market_touch"):
        margin = 0.0
        if len(operands) > 2:
            margin_operand = operands[2]
            if margin_operand.get("type") == "margin":
                margin = float((margin_operand.get("definition") or {}).get("value", 0)) / 100.0
        if operator == "market_breakthrough":
            return _crossed(left, right * (1 + margin) if not isinstance(right, pd.Series)
                            else right * (1 + margin), up=True)
        band_low = right * (1 - margin)
        band_high = right * (1 + margin)
        touched = (left <= band_high) & (left >= band_low)
        if operator == "market_touch":
            return touched
        return touched & (left > left.shift(1))  # bounce: touched, then turning up

    raise UnsupportedCondition(f"operator {operator!r} not supported")


def _evaluate_block(block: dict, df: pd.DataFrame) -> pd.Series:
    """A logic block: its own conditions plus any nested sub-blocks."""
    verdicts: list[pd.Series] = []

    for condition in block.get("conditions") or []:
        verdicts.append(_evaluate_condition(condition, df).fillna(False).astype(bool))
    for sub in block.get("subBlocks") or []:
        inner = sub.get("script") if "script" in sub else sub
        verdicts.append(_evaluate_block(inner, df))

    if not verdicts:
        return pd.Series(False, index=df.index)

    logic = (block.get("logicCondition") or "and").lower()
    combined = verdicts[0]
    for verdict in verdicts[1:]:
        combined = (combined & verdict) if logic == "and" else (combined | verdict)
    if logic == "none_of":
        combined = ~combined

    # "happened within the last N bars" rather than strictly on this bar.
    if str(block.get("useRange", "no")).lower() not in ("no", "false", ""):
        window = int(block.get("withinRange") or 1)
        if window > 1:
            combined = combined.rolling(window, min_periods=1).max().astype(bool)

    return combined


def evaluate_signal_tree(root: dict | None, df: pd.DataFrame) -> pd.Series:
    """Top-level entry/exit tree -> boolean Series aligned to `df`.

    Non-`script` entries (stop_loss, take_profit, trailing_stop,
    x_candles_passed) are risk-management settings, not bar conditions --
    they are handled by the execution engine, so they're skipped here.
    """
    if not root:
        return pd.Series(False, index=df.index)

    verdicts: list[pd.Series] = []
    for entry in root.get("conditions") or []:
        if entry.get("type") != "script":
            continue
        block = entry.get("script") or {}
        verdicts.append(_evaluate_block(block, df))

    if not verdicts:
        return pd.Series(False, index=df.index)

    combined = verdicts[0]
    for verdict in verdicts[1:]:
        combined = combined & verdict
    return combined.fillna(False).astype(bool)

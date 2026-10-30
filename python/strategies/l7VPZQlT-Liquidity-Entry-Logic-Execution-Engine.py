"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Liquidity Entry Logic v14 – Execution Engine
Author       : JamesK318
Source URL   : https://www.tradingview.com/script/l7VPZQlT-Liquidity-Entry-Logic-Execution-Engine
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). The high / low of the Asian session (18:00 - 24:00 exchange time) are tracked from its first bar and kept afterwards. Each side gets a score: a confirmed liquidity sweep of the Asian extreme (wick over 45 % of the bar, closing back with the bar's colour) counts 2, an impulse candle, the stacked chart EMAs 21 / 321 / 440,
the 4-hour mid EMA over (under) the slow EMA (request.security, lookahead off), the 09:30 - 12:00 window, a trending regime and a non-choppy regime count 1 each. A score at or above the A+ threshold (or 4 when only A+ is off) enters; the entry reverses an opposite position and one exit order per side (ATR stop and target from the signal close) is re-issued every bar.
Deviations from the original: none.
Not carried over: nothing (no display code in the source).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, pmath, ta


class LiquidityEntryLogic(Script):
    TITLE = "Liquidity Entry Logic v14 – Execution Engine"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "l7VPZQlT", "author": "JamesK318", "licence": "not stated",
              "url": "https://www.tradingview.com/script/l7VPZQlT-Liquidity-Entry-Logic-Execution-Engine"}

    def init(self):
        i = self.input
        self.fast_len = i.int(21)
        self.mid_len = i.int(321)
        self.slow_len = i.int(440)
        self.htf_tf = i.timeframe("240")
        self.atr_len = i.int(14)
        self.sl_atr = i.float(1.5)
        self.tp_atr = i.float(3.0)
        self.min_aplus_score = i.int(6, "A+ Threshold (0–8)")
        self.only_aplus = i.bool(True, "Only Take A+ Trades")
        self.asia_session = i.session("1800-0000")
        self.ny_session = i.session("0930-1200")
        self.asia_high = NA
        self.asia_low = NA
        self.prev_in_asia = False
        self.long_sl = self.long_tp = self.short_sl = self.short_tp = NA

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        mid_ema = ta.ema(close, self.mid_len)
        slow_ema = ta.ema(close, self.slow_len)
        htf_mid = self.security(None, self.htf_tf, lambda v: ta.ema(v.close, self.mid_len))
        htf_slow = self.security(None, self.htf_tf, lambda v: ta.ema(v.close, self.slow_len))
        bull_htf = htf_mid > htf_slow
        bear_htf = htf_mid < htf_slow
        in_asia = self.time_in_session(self.asia_session)
        in_ny = self.time_in_session(self.ny_session)
        if in_asia and not self.prev_in_asia:
            self.asia_high = float(high)
            self.asia_low = float(low)
        self.prev_in_asia = bool(in_asia)
        if in_asia:
            self.asia_high = pmath.max(self.asia_high, high)
            self.asia_low = pmath.min(self.asia_low, low)
        range_size = ta.sma(high - low, 20)
        trend_size = abs(close - self.close[10])
        is_trending = trend_size > range_size * 1.2
        is_choppy = ta.sma(range_size, 10) < ta.sma(range_size, 50)
        wick = high - low
        upper_w = high - pmath.max(open_, close)
        lower_w = pmath.min(open_, close) - low
        raw_sweep_high = high > self.asia_high and upper_w > wick * 0.45
        raw_sweep_low = low < self.asia_low and lower_w > wick * 0.45
        confirmed_sweep_high = raw_sweep_high and close < open_
        confirmed_sweep_low = raw_sweep_low and close > open_
        avg_range = ta.sma(high - low, 10)
        bull_impulse = close > open_ and (high - low) > avg_range * 1.3
        bear_impulse = close < open_ and (high - low) > avg_range * 1.3
        trend_bull = close > mid_ema and mid_ema > slow_ema
        trend_bear = close < mid_ema and mid_ema < slow_ema
        bull_score = ((2 if confirmed_sweep_low else 0) + (1 if bull_impulse else 0) + (1 if trend_bull else 0) + (1 if bull_htf else 0)
                      + (1 if in_ny else 0) + (1 if is_trending else 0) + (1 if not is_choppy else 0))
        bear_score = ((2 if confirmed_sweep_high else 0) + (1 if bear_impulse else 0) + (1 if trend_bear else 0) + (1 if bear_htf else 0)
                      + (1 if in_ny else 0) + (1 if is_trending else 0) + (1 if not is_choppy else 0))
        long_condition = bull_score >= self.min_aplus_score
        short_condition = bear_score >= self.min_aplus_score
        long_condition = long_condition if self.only_aplus else (bull_score >= 4)
        short_condition = short_condition if self.only_aplus else (bear_score >= 4)
        atr = ta.atr(self.atr_len)
        self.long_sl = close - atr * self.sl_atr
        self.long_tp = close + atr * self.tp_atr
        self.short_sl = close + atr * self.sl_atr
        self.short_tp = close - atr * self.tp_atr
        if long_condition and st.position_size <= 0:
            st.entry("Long", st.long)
        if short_condition and st.position_size >= 0:
            st.entry("Short", st.short)
        st.exit("L Exit", from_entry="Long", stop=self.long_sl, limit=self.long_tp)
        st.exit("S Exit", from_entry="Short", stop=self.short_sl, limit=self.short_tp)

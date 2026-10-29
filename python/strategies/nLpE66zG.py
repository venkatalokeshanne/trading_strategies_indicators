"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : XAUUSD Wyckoff Second Breakout V3 Candle RR
Author       : zhangwenjian810
Source URL   : https://www.tradingview.com/script/nLpE66zG
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). A staged "second breakout" per side: a close above the last pivot high is the first break (stage 1, the break level and the running high / pull-back low are recorded); while in stage 1 each bar extends the running extremes and, once a close falls below the running high, stage 2 starts (stage 1 is abandoned after the wait limit);
in stage 2, a close above the running high while flat enters long with the stop under the pull-back low (ATR buffer) and a target at a risk multiple chosen by the candle (trend expansion, low liquidity or normal); shorts mirror it. The entry and its exit order are issued together.
Deviations from the original: none.
Not carried over: nothing (no display code in the source).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, pmath, ta


class WyckoffSecondBreakout(Script):
    TITLE = "XAUUSD Wyckoff Second Breakout V3 Candle RR"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, pyramiding=0, commission_type="percent", commission_value=0.02, slippage=2)
    SOURCE = {"id": "nLpE66zG", "author": "zhangwenjian810", "licence": "not stated", "url": "https://www.tradingview.com/script/nLpE66zG"}

    def init(self):
        i = self.input
        self.left_bars = i.int(4, "Pivot Left Bars", minval=1)
        self.right_bars = i.int(2, "Pivot Right Bars", minval=1)
        self.max_wait_bars = i.int(20, "Max Bars After First Breakout", minval=1)
        self.atr_len = i.int(14, "ATR Length", minval=1)
        self.stop_buffer_atr = i.float(0.2, "Structure Stop Buffer ATR", step=0.1)
        self.body_avg_len = i.int(50, "Body Average Length", minval=1)
        self.range_avg_len = i.int(100, "Range Average Length", minval=1)
        self.low_liq_lookback = i.int(10, "Low Liquidity Lookback", minval=1)
        self.low_liq_mult = i.float(0.75, "Low Liquidity Multiplier", step=0.05)
        self.trend_body_mult = i.float(1.5, "Trend Body Expansion Multiplier", step=0.1)
        self.trend_range_atr_mult = i.float(1.0, "Trend Range ATR Multiplier", step=0.1)
        self.strong_close_pct = i.float(0.30, "Strong Close Position", step=0.05)
        self.rr_low_liquidity = i.float(1.0, "RR Low Liquidity", step=0.1)
        self.rr_normal = i.float(2.0, "RR Normal", step=0.1)
        self.rr_trend = i.float(3.0, "RR Trend Expansion", step=0.1)
        self.use_long = i.bool(True, "Enable Long")
        self.use_short = i.bool(True, "Enable Short")
        self.last_pivot_high = NA
        self.last_pivot_low = NA
        self.long_stage = 0
        self.long_h = NA
        self.long_h2 = NA
        self.long_pullback_low = NA
        self.long_bars_after_break = 0
        self.short_stage = 0
        self.short_l = NA
        self.short_l2 = NA
        self.short_bounce_high = NA
        self.short_bars_after_break = 0

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        atr = ta.atr(self.atr_len)
        body = abs(close - open_)
        bar_range = high - low
        avg_body = ta.sma(body, self.body_avg_len)
        avg_range = ta.sma(bar_range, self.range_avg_len)
        recent_body = ta.sma(body, self.low_liq_lookback)
        recent_range = ta.sma(bar_range, self.low_liq_lookback)
        low_liquidity = recent_body < avg_body * self.low_liq_mult and recent_range < avg_range * self.low_liq_mult
        long_strong_close = close >= high - bar_range * self.strong_close_pct if bar_range > 0 else False
        short_strong_close = close <= low + bar_range * self.strong_close_pct if bar_range > 0 else False
        long_trend_expansion = close > open_ and body > avg_body * self.trend_body_mult and bar_range > atr * self.trend_range_atr_mult and long_strong_close
        short_trend_expansion = close < open_ and body > avg_body * self.trend_body_mult and bar_range > atr * self.trend_range_atr_mult and short_strong_close
        pivot_high = ta.pivothigh(high, self.left_bars, self.right_bars)
        pivot_low = ta.pivotlow(low, self.left_bars, self.right_bars)
        if not na(pivot_high):
            self.last_pivot_high = pivot_high
        if not na(pivot_low):
            self.last_pivot_low = pivot_low
        first_long_break = self.use_long and self.long_stage == 0 and (not na(self.last_pivot_high)) and close > self.last_pivot_high
        if first_long_break:
            self.long_stage = 1
            self.long_h = self.last_pivot_high
            self.long_h2 = float(high)
            self.long_pullback_low = float(low)
            self.long_bars_after_break = 0
        if self.long_stage == 1:
            self.long_bars_after_break += 1
            self.long_h2 = pmath.max(self.long_h2, high)
            self.long_pullback_low = pmath.min(self.long_pullback_low, low)
            if close < self.long_h2:
                self.long_stage = 2
            if self.long_bars_after_break > self.max_wait_bars:
                self.long_stage = 0
                self.long_h = NA
                self.long_h2 = NA
                self.long_pullback_low = NA
        if self.long_stage == 2:
            self.long_bars_after_break += 1
            self.long_pullback_low = pmath.min(self.long_pullback_low, low)
        long_second_break = self.use_long and self.long_stage == 2 and close > self.long_h2 and st.position_size == 0
        if long_second_break:
            long_stop = self.long_pullback_low - self.stop_buffer_atr * atr
            long_risk = close - long_stop
            long_rr = self.rr_trend if long_trend_expansion else (self.rr_low_liquidity if low_liquidity else self.rr_normal)
            long_target = close + long_rr * long_risk
            if long_risk > 0:
                st.entry("Long", st.long)
                st.exit("Long Exit", "Long", stop=long_stop, limit=long_target)
            self.long_stage = 0
            self.long_h = NA
            self.long_h2 = NA
            self.long_pullback_low = NA
        if self.long_stage == 2 and self.long_bars_after_break > self.max_wait_bars:
            self.long_stage = 0
            self.long_h = NA
            self.long_h2 = NA
            self.long_pullback_low = NA
        first_short_break = self.use_short and self.short_stage == 0 and (not na(self.last_pivot_low)) and close < self.last_pivot_low
        if first_short_break:
            self.short_stage = 1
            self.short_l = self.last_pivot_low
            self.short_l2 = float(low)
            self.short_bounce_high = float(high)
            self.short_bars_after_break = 0
        if self.short_stage == 1:
            self.short_bars_after_break += 1
            self.short_l2 = pmath.min(self.short_l2, low)
            self.short_bounce_high = pmath.max(self.short_bounce_high, high)
            if close > self.short_l2:
                self.short_stage = 2
            if self.short_bars_after_break > self.max_wait_bars:
                self.short_stage = 0
                self.short_l = NA
                self.short_l2 = NA
                self.short_bounce_high = NA
        if self.short_stage == 2:
            self.short_bars_after_break += 1
            self.short_bounce_high = pmath.max(self.short_bounce_high, high)
        short_second_break = self.use_short and self.short_stage == 2 and close < self.short_l2 and st.position_size == 0
        if short_second_break:
            short_stop = self.short_bounce_high + self.stop_buffer_atr * atr
            short_risk = short_stop - close
            short_rr = self.rr_trend if short_trend_expansion else (self.rr_low_liquidity if low_liquidity else self.rr_normal)
            short_target = close - short_rr * short_risk
            if short_risk > 0:
                st.entry("Short", st.short)
                st.exit("Short Exit", "Short", stop=short_stop, limit=short_target)
            self.short_stage = 0
            self.short_l = NA
            self.short_l2 = NA
            self.short_bounce_high = NA
        if self.short_stage == 2 and self.short_bars_after_break > self.max_wait_bars:
            self.short_stage = 0
            self.short_l = NA
            self.short_l2 = NA
            self.short_bounce_high = NA

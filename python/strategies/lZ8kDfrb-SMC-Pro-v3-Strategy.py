"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : SMC Pro v3 Strategy - Liquidity Sweeps + FVG + BOS/CHoCH
Author       : not stated
Source URL   : https://www.tradingview.com/script/lZ8kDfrb
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market entries at the next open, 10 % of equity, 0.01 % commission, pyramiding 0). A long needs, within
the last 8 bars, a liquidity sweep (a bar that trades under the last swing low / previous day's low and closes back above it),
the current bar overlapping the latest bullish fair-value gap or displacement zone, a bullish confirmation candle breaking the
previous high, a close in the discount half of the 40-bar range and EMA20 over EMA50; shorts mirror. The stop is the signal
bar's low (high), the target 2 R; the stop moves to break-even once the high (low) has gone 1 R. The previous day's high / low come
from request.security("D", high[1] / low[1]) with lookahead on.
Deviations from the original: none.
Not carried over: boxes, labels, lines, plots, alerts.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, ta


def _na(x):
    return x != x


class SmcProV3(Script):
    TITLE = "SMC Pro v3 Strategy - Liquidity Sweeps + FVG + BOS/CHoCH"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, currency="USD", default_qty_type="percent_of_equity", default_qty_value=10,
                    pyramiding=0, commission_type="percent", commission_value=0.01)
    SOURCE = {"id": "lZ8kDfrb", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/lZ8kDfrb"}

    def init(self):
        i = self.input
        self.swing_len = i.int(5, "Swing Length", minval=2, group="Structure")
        self.sweep_lookback = i.int(8, "Sweep Lookback Bars", minval=1, group="Liquidity")
        self.fvg_min_atr_mult = i.float(0.15, "Min FVG Size ATR Mult", step=0.05, group="Fair Value Gaps")
        self.only_fresh_fvg = i.bool(True, "Only Freshest FVG", group="Fair Value Gaps")
        self.show_fvg = i.bool(True, "Show FVG", group="Fair Value Gaps")
        self.show_zones = i.bool(True, "Show Institutional Zones", group="Institutional Zones")
        self.zone_atr_mult = i.float(0.8, "Displacement Threshold ATR Mult", step=0.1, group="Institutional Zones")
        self.use_trend_filter = i.bool(True, "Use EMA Trend Filter", group="Trend Filter")
        self.fast_ema = i.int(20, "Fast EMA", minval=1, group="Trend Filter")
        self.slow_ema = i.int(50, "Slow EMA", minval=1, group="Trend Filter")
        self.use_pd_filter = i.bool(True, "Use Premium / Discount Filter", group="Premium / Discount")
        self.pd_lookback = i.int(40, "PD Range Lookback", minval=5, group="Premium / Discount")
        self.confirm_break = i.bool(True, "Require Confirmation Break", group="Signals / Execution")
        self.allow_longs = i.bool(True, "Allow Longs", group="Signals / Execution")
        self.allow_shorts = i.bool(True, "Allow Shorts", group="Signals / Execution")
        self.one_trade = i.bool(True, "One Trade At A Time", group="Signals / Execution")
        self.use_swing_stops = i.bool(True, "Use Signal Candle Swing Stop", group="Risk Management")
        self.atr_stop_mult = i.float(1.0, "ATR Stop Mult (if not using swing stop)", minval=0.1, step=0.1, group="Risk Management")
        self.rr_target = i.float(2.0, "Take Profit RR", minval=0.5, step=0.5, group="Risk Management")
        self.use_trailing = i.bool(False, "Use Trailing Stop", group="Risk Management")
        self.trail_atr_mult = i.float(1.0, "Trail ATR Mult", minval=0.1, step=0.1, group="Risk Management")
        self.move_to_be = i.bool(True, "Move Stop to Breakeven at 1R", group="Risk Management")
        # var state
        self.last_swing_high = self.last_swing_low = NA
        self.trend_state = 0
        self.bull_fvg_top = self.bull_fvg_bot = self.bear_fvg_top = self.bear_fvg_bot = NA
        self.bull_zone_top = self.bull_zone_bot = self.bear_zone_top = self.bear_zone_bot = NA
        self.long_sl = self.long_tp = self.long_entry = self.long_risk = NA
        self.short_sl = self.short_tp = self.short_entry = self.short_risk = NA

    def on_bar(self):
        close, open_, high, low = float(self.close), float(self.open), float(self.high), float(self.low)
        high_1, low_1, close_1, open_1 = self.high[1], self.low[1], self.close[1], self.open[1]
        high_2, low_2 = self.high[2], self.low[2]

        atr = ta.atr(14)
        ema_fast = ta.ema(self.close, self.fast_ema)
        ema_slow = ta.ema(self.close, self.slow_ema)
        bull_trend = ema_fast > ema_slow
        bear_trend = ema_fast < ema_slow

        ph = ta.pivothigh(self.high, self.swing_len, self.swing_len)
        pl = ta.pivotlow(self.low, self.swing_len, self.swing_len)
        if not _na(ph):
            self.last_swing_high = float(ph)
        if not _na(pl):
            self.last_swing_low = float(pl)

        bull_break = (not _na(self.last_swing_high)) and close > self.last_swing_high
        bear_break = (not _na(self.last_swing_low)) and close < self.last_swing_low
        if bull_break:
            self.trend_state = 1
        if bear_break:
            self.trend_state = -1

        prev_day_high = self.security(self.syminfo.tickerid, "D", lambda v: v.high[1], lookahead=True)
        prev_day_low = self.security(self.syminfo.tickerid, "D", lambda v: v.low[1], lookahead=True)

        range_high = ta.highest(self.high, self.pd_lookback)
        range_low = ta.lowest(self.low, self.pd_lookback)
        eq = (range_high + range_low) / 2.0
        in_premium = close > eq
        in_discount = close < eq

        bear_sweep = (not _na(self.last_swing_high)) and high > self.last_swing_high and close < self.last_swing_high
        bull_sweep = (not _na(self.last_swing_low)) and low < self.last_swing_low and close > self.last_swing_low
        pdh_sweep = high > prev_day_high and close < prev_day_high
        pdl_sweep = low < prev_day_low and close > prev_day_low
        bs_bear = ta.barssince(bear_sweep or pdh_sweep)
        bs_bull = ta.barssince(bull_sweep or pdl_sweep)
        recent_bear_sweep = bs_bear >= 0 and bs_bear <= self.sweep_lookback
        recent_bull_sweep = bs_bull >= 0 and bs_bull <= self.sweep_lookback

        bull_fvg = low > high_2 and (low - high_2) > atr * self.fvg_min_atr_mult
        bear_fvg = high < low_2 and (low_2 - high) > atr * self.fvg_min_atr_mult
        if self.show_fvg and bull_fvg:
            self.bull_fvg_top = low
            self.bull_fvg_bot = float(high_2)
        if self.show_fvg and bear_fvg:
            self.bear_fvg_top = float(low_2)
            self.bear_fvg_bot = high
        in_bull_fvg = (not _na(self.bull_fvg_top)) and low <= self.bull_fvg_top and high >= self.bull_fvg_bot
        in_bear_fvg = (not _na(self.bear_fvg_top)) and high >= self.bear_fvg_bot and low <= self.bear_fvg_top

        bull_displacement = close > high_1 and (close - open_) > atr * self.zone_atr_mult
        bear_displacement = close < low_1 and (open_ - close) > atr * self.zone_atr_mult
        if self.show_zones and bull_displacement and close_1 < open_1:
            self.bull_zone_top = max(open_1, close_1)
            self.bull_zone_bot = float(low_1)
        if self.show_zones and bear_displacement and close_1 > open_1:
            self.bear_zone_top = float(high_1)
            self.bear_zone_bot = min(open_1, close_1)
        in_bull_zone = (not _na(self.bull_zone_top)) and low <= self.bull_zone_top and high >= self.bull_zone_bot
        in_bear_zone = (not _na(self.bear_zone_top)) and high >= self.bear_zone_bot and low <= self.bear_zone_top

        bull_confirm = (close > open_ and close > high_1) if self.confirm_break else (close > open_)
        bear_confirm = (close < open_ and close < low_1) if self.confirm_break else (close < open_)

        long_ctx = recent_bull_sweep and (in_bull_zone or in_bull_fvg) and bull_confirm \
            and ((not self.use_pd_filter) or in_discount) and ((not self.use_trend_filter) or bull_trend)
        short_ctx = recent_bear_sweep and (in_bear_zone or in_bear_fvg) and bear_confirm \
            and ((not self.use_pd_filter) or in_premium) and ((not self.use_trend_filter) or bear_trend)

        st = self.strategy
        can_enter = (st.position_size == 0) if self.one_trade else True
        long_signal = self.allow_longs and long_ctx and can_enter
        short_signal = self.allow_shorts and short_ctx and can_enter

        mintick = self.syminfo.mintick
        if long_signal:
            self.long_entry = close
            self.long_sl = low if self.use_swing_stops else close - atr * self.atr_stop_mult
            self.long_risk = self.long_entry - self.long_sl
            self.long_tp = self.long_entry + self.long_risk * self.rr_target
            if self.long_risk > mintick:
                st.entry("Long", st.long)
        if short_signal:
            self.short_entry = close
            self.short_sl = high if self.use_swing_stops else close + atr * self.atr_stop_mult
            self.short_risk = self.short_sl - self.short_entry
            self.short_tp = self.short_entry - self.short_risk * self.rr_target
            if self.short_risk > mintick:
                st.entry("Short", st.short)

        long_active = st.position_size > 0
        short_active = st.position_size < 0
        curr_long_sl = self.long_sl
        curr_short_sl = self.short_sl
        if long_active and self.move_to_be and not _na(self.long_entry) and not _na(self.long_risk):
            if high >= self.long_entry + self.long_risk:
                curr_long_sl = max(curr_long_sl, self.long_entry)
        if short_active and self.move_to_be and not _na(self.short_entry) and not _na(self.short_risk):
            if low <= self.short_entry - self.short_risk:
                curr_short_sl = min(curr_short_sl, self.short_entry)
        if long_active and self.use_trailing:
            curr_long_sl = max(curr_long_sl, close - atr * self.trail_atr_mult)
        if short_active and self.use_trailing:
            curr_short_sl = min(curr_short_sl, close + atr * self.trail_atr_mult)
        if long_active and not _na(curr_long_sl) and not _na(self.long_tp):
            st.exit("Long Exit", from_entry="Long", stop=curr_long_sl, limit=self.long_tp)
        if short_active and not _na(curr_short_sl) and not _na(self.short_tp):
            st.exit("Short Exit", from_entry="Short", stop=curr_short_sl, limit=self.short_tp)

        self.plot(eq, title="EQ")

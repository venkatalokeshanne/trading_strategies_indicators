"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : VWAP Mean Reversion Strategy
Author       : not stated
Source URL   : https://www.tradingview.com/script/YBqnzqDK
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open, stop / limit orders on the bar path). A shooting-star / hammer / doji setup bar at a 20-bar extreme, followed by a confirming bar (engulfing, or a lower-high close under / higher-low close over the previous bar, closing in the outer 30 % of its range and not larger than 1.5 ATR), with the previous close outside the 1-sigma session-VWAP band, produces one signal (the first bar of a run). The signal stores a stop one ATR-buffer beyond the setup bar, an entry one buffer beyond its extreme and a target at 2 x risk, sizes the order to risk 1 % of equity (rounded down) and places a stop order at the entry level (cancelled after 2 bars) or - the default - a limit order at the close plus buffer and spread. A stop / limit exit order with the stored levels (minus / plus the spread) is re-issued every bar; an opposite signal closes the other side.
Assumptions: input.timeframe("Chart") is the chart's own timeframe (so the adaptive ATR length equals the base length); an entry order with quantity 0 is not placed.
Deviations from the original: none known.
Not carried over: plots, shapes and the unused P&L bookkeeping.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, nz, pmath, ta


def _tf_minutes(tf):
    return {"1": 1, "3": 3, "5": 5, "15": 15, "30": 30, "45": 45, "60": 60, "120": 120, "180": 180, "240": 240, "D": 1440, "W": 10080, "M": 43200}.get(tf, 1440)


class VwapMeanReversion(Script):
    TITLE = "VWAP Mean Reversion Strategy"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="fixed", default_qty_value=0)
    SOURCE = {"id": "YBqnzqDK", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/YBqnzqDK"}

    def init(self):
        i = self.input
        self.lookback = i.int(20, "High/Low Lookback Length", minval=2)
        self.body_pct_ss = i.float(0.3, "Max Body % (SS/Hammer)", step=0.05)
        self.upper_wick_mult = i.float(2.0, "Upper Wick to Body Multiple (SS)", step=0.1)
        self.lower_wick_mult = i.float(2.0, "Lower Wick to Body Multiple (Hammer)", step=0.1)
        self.doji_body_pct = i.float(0.2, "Max Body % of Range (Doji)", step=0.02)
        self.close_percent = i.float(0.30, "Close Position % (Top/Bottom of Range)", step=0.05)
        self.use_adaptive_atr = i.bool(True, "Use Adaptive ATR")
        self.base_atr_len = i.int(10, "Base ATR Length (on target TF)")
        self.target_tf = i.timeframe("", "Target Timeframe for ATR")
        self.atr_multiplier = i.float(1.5, "Max Candle Size (x ATR)", step=0.1)
        self.risk_perc = i.float(1.0, "Risk % per Trade", step=0.1) / 100
        self.stop_atr = i.float(0.2, "Stop Loss (x ATR)")
        self.tp_risk_mult = i.float(2.0, "Take Profit (x Risk)", step=0.1)
        self.enable_close_opposite = i.bool(True, "Enable Close Opposite Signal")
        self.entry_type = i.string("Close of Confirmation", "Entry Type", options=["Stop", "Close of Confirmation"])
        self.close_entry_buffer_perc = i.float(0.01, "Close Entry Buffer %", step=0.001)
        self.engulfing_only = i.bool(False, "Engulfing Candles Only for Entries")
        self.spread_points = i.float(0.09, "Broker Spread (in price units)", step=0.01)
        self.use_vwap_filter = i.bool(True, "Require Price Outside 1σ")
        self.use_mean_reversion = i.bool(True, "Enable Mean Reversion Logic")
        self.atr_buffer_perc = i.float(0.01, "ATR Buffer %", step=0.001)
        self.cum_vol = NA
        self.cum_pv = NA
        self.cum_pv2 = NA
        self.long_stop = NA
        self.long_target = NA
        self.short_stop = NA
        self.short_target = NA
        self.long_signal_bar = NA
        self.short_signal_bar = NA

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        h_bse, h_bue, h_bc, h_bl = self.H("bse"), self.H("bue"), self.H("bc"), self.H("bl")
        bse_1, bue_1, bc_1, bl_1 = h_bse[1], h_bue[1], h_bc[1], h_bl[1]
        close_1, open_1, high_1, low_1 = self.close[1], self.open[1], self.high[1], self.low[1]
        chart_min = _tf_minutes(self.timeframe.period)
        target_min = _tf_minutes(self.target_tf)
        adaptive_len = pmath.max(1, pmath.round(self.base_atr_len * div(target_min, chart_min)))

        day_chg = ta.change(self.time_fn("D"))
        new_session = (not na(day_chg)) and day_chg != 0
        hlc3 = float(self.hlc3)
        vol = float(self.volume)
        self.cum_vol = vol if new_session else self.cum_vol + vol
        self.cum_pv = hlc3 * vol if new_session else self.cum_pv + hlc3 * vol
        self.cum_pv2 = (hlc3 * hlc3) * vol if new_session else self.cum_pv2 + (hlc3 * hlc3) * vol
        vwap = div(self.cum_pv, self.cum_vol)
        variance = div(self.cum_pv2, self.cum_vol) - pmath.pow(vwap, 2)
        stdev = pmath.sqrt(pmath.max(variance, 0))
        upper_band = vwap + stdev
        lower_band = vwap - stdev
        price_above_upper = close_1 > upper_band
        price_below_lower = close_1 < lower_band

        atr = ta.atr(adaptive_len) if self.use_adaptive_atr else ta.atr(self.base_atr_len)
        body = abs(close - open_)
        candle = high - low
        upper_wick = high - pmath.max(open_, close)
        lower_wick = pmath.min(open_, close) - low
        valid_range = candle > 0
        atr_valid = candle <= (atr * self.atr_multiplier)
        close_pos = div(close - low, candle) if valid_range else 0.0
        small_body_ss = valid_range and body <= candle * self.body_pct_ss
        long_upper_wick = valid_range and upper_wick >= body * self.upper_wick_mult
        small_lower_wick = valid_range and lower_wick <= body
        shooting_star = small_body_ss and long_upper_wick and small_lower_wick
        small_body_hammer = valid_range and body <= candle * self.body_pct_ss
        long_lower_wick = valid_range and lower_wick >= body * self.lower_wick_mult
        small_upper_wick_hammer = valid_range and upper_wick <= body
        hammer = small_body_hammer and long_lower_wick and small_upper_wick_hammer
        doji = valid_range and body <= candle * self.doji_body_pct
        twenty_high = ta.highest(high, self.lookback)
        twenty_low = ta.lowest(low, self.lookback)
        bearish_setup = (shooting_star or doji) and high >= twenty_high
        bullish_setup = (hammer or doji) and low <= twenty_low
        bearish_engulfing = close < open_ and close_1 > open_1 and open_ >= close_1 and close <= open_1
        bullish_engulfing = close > open_ and close_1 < open_1 and open_ <= close_1 and close >= open_1
        lower_high_close_below_low = high < high_1 and close < low_1
        higher_low_close_above_high = low > low_1 and close > high_1
        bullish_close_valid = close_pos >= (1 - self.close_percent)
        bearish_close_valid = close_pos <= self.close_percent
        bear_base = (bse_1 == 1) and bearish_close_valid and atr_valid
        bull_base = (bue_1 == 1) and bullish_close_valid and atr_valid
        if self.engulfing_only:
            bear_base = bear_base and bearish_engulfing
            bull_base = bull_base and bullish_engulfing
        else:
            bear_base = bear_base and (bearish_engulfing or lower_high_close_below_low)
            bull_base = bull_base and (bullish_engulfing or higher_low_close_above_high)
        bearish_confirmed = bear_base
        bullish_confirmed = bull_base
        if self.use_vwap_filter:
            bearish_confirmed = bearish_confirmed and price_above_upper
            bullish_confirmed = bullish_confirmed and price_below_lower
        if self.use_mean_reversion:
            bearish_confirmed = bearish_confirmed and price_above_upper
            bullish_confirmed = bullish_confirmed and price_below_lower
        long_signal_once = bullish_confirmed and not (bc_1 == 1)
        short_signal_once = bearish_confirmed and not (bl_1 == 1)

        atr_buffer = atr * self.atr_buffer_perc
        close_entry_buffer = atr * self.close_entry_buffer_perc
        if long_signal_once:
            self.long_signal_bar = self.bar_index
            self.long_stop = low - atr_buffer
            long_entry = high + atr_buffer
            long_risk = pmath.max(long_entry - self.long_stop, atr * self.stop_atr)
            self.long_target = long_entry + (long_risk * self.tp_risk_mult)
            long_qty = pmath.floor(div(st.equity * self.risk_perc, long_risk)) if long_risk > 0 else 0
            eff_long = long_entry + self.spread_points if self.entry_type == "Stop" else close + close_entry_buffer + self.spread_points
            if long_qty > 0:
                if self.entry_type == "Stop":
                    st.entry("Long", st.long, qty=long_qty, stop=eff_long)
                else:
                    st.entry("Long", st.long, qty=long_qty, limit=eff_long)
        if short_signal_once:
            self.short_signal_bar = self.bar_index
            self.short_stop = high + atr_buffer
            short_entry = low - atr_buffer
            short_risk = pmath.max(self.short_stop - short_entry, atr * self.stop_atr)
            self.short_target = short_entry - (short_risk * self.tp_risk_mult)
            short_qty = pmath.floor(div(st.equity * self.risk_perc, short_risk)) if short_risk > 0 else 0
            eff_short = short_entry - self.spread_points if self.entry_type == "Stop" else close - close_entry_buffer - self.spread_points
            if short_qty > 0:
                if self.entry_type == "Stop":
                    st.entry("Short", st.short, qty=short_qty, stop=eff_short)
                else:
                    st.entry("Short", st.short, qty=short_qty, limit=eff_short)
        if self.entry_type == "Stop":
            if (not na(self.long_signal_bar)) and self.bar_index - self.long_signal_bar > 2:
                st.cancel("Long")
                self.long_signal_bar = NA
            if (not na(self.short_signal_bar)) and self.bar_index - self.short_signal_bar > 2:
                st.cancel("Short")
                self.short_signal_bar = NA
        st.exit("Long Exit", from_entry="Long", stop=self.long_stop - self.spread_points, limit=self.long_target - self.spread_points)
        st.exit("Short Exit", from_entry="Short", stop=self.short_stop + self.spread_points, limit=self.short_target + self.spread_points)
        if self.enable_close_opposite:
            if long_signal_once:
                st.close("Short")
            if short_signal_once:
                st.close("Long")
        h_bse.set(1 if bearish_setup else 0)
        h_bue.set(1 if bullish_setup else 0)
        h_bc.set(1 if bullish_confirmed else 0)
        h_bl.set(1 if bearish_confirmed else 0)

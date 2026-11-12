"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Volume-Confirmed Support/Resistance Breakout Strategy
Author       : blitz_locked
Source URL   : https://www.tradingview.com/script/CItvSvqk-Breakout-Pulse-Volume-Confirmed-Support-Resistance-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. The latest confirmed pivot high / low is the resistance / support. A close crossing it on a volume surge (volume above its SMA times a multiplier), with the close on
the right side of the EMA (optional) and inside the date range, enters (reversing) with a structural or ATR stop and an ATR target that are placed once the position exists.
The stop / target variables are cleared on every bar that finds the position flat after having been open on the previous bar - which also wipes the levels just set by a breakout on the very bar a trade ended, as in the original.

Deviations from the original: none.
Not carried over: the position-coloured candles, glow lines, channel gradient and alerts (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, ta


class VolumeConfirmedSrBreakout(Script):
    TITLE = "Volume-Confirmed Support/Resistance Breakout Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=10, commission_type="percent", commission_value=0.01, slippage=2, pyramiding=0)
    SOURCE = {"id": "CItvSvqk", "author": "blitz_locked", "licence": "not stated",
              "url": "https://www.tradingview.com/script/CItvSvqk-Breakout-Pulse-Volume-Confirmed-Support-Resistance-Strategy"}

    def init(self):
        g = "✧ Support / Resistance ✧"
        self.pivot_left = self.input.int(10, "Pivot Left Bars", minval=1, group=g)
        self.pivot_right = self.input.int(10, "Pivot Right Bars", minval=1, group=g)
        g = "✧ Volume Confirmation ✧"
        self.vol_length = self.input.int(20, "Volume Average Length", minval=1, group=g)
        self.vol_multiplier = self.input.float(1.5, "Volume Surge Multiplier", minval=1.0, step=0.1, group=g)
        g = "✧ Trend Filter ✧"
        self.use_trend_filter = self.input.bool(True, "Require EMA trend filter", group=g)
        self.ema_length = self.input.int(200, "EMA Length", minval=1, group=g)
        g = "✧ Risk Management ✧"
        self.atr_length = self.input.int(14, "ATR Length", minval=1, group=g)
        self.atr_stop_mult = self.input.float(1.5, "ATR Stop Multiplier", minval=0.1, step=0.1, group=g)
        self.atr_target_mult = self.input.float(3.0, "ATR Target Multiplier", minval=0.1, step=0.1, group=g)
        self.use_struct_stop = self.input.bool(True, "Use broken swing level as stop (else pure ATR)", group=g)
        self.stop_buffer_atr = self.input.float(0.25, "Structural Stop ATR Buffer", minval=0.0, step=0.05, group=g)
        g = "✧ Backtest Range ✧"
        self.start_date = self.input.time(1514764800000, "Start Date", group=g)      # timestamp("01 Jan 2018 00:00 +0000")
        self.end_date = self.input.time(1767139200000, "End Date", group=g)          # timestamp("31 Dec 2025 00:00 +0000")
        self.resistance = NA
        self.support = NA
        self.long_stop_price = NA
        self.long_tgt_price = NA
        self.short_stop_price = NA
        self.short_tgt_price = NA

    def on_bar(self):
        st = self.strategy
        pos_h = self.H("pos")
        pos_1 = pos_h[1]
        pos_h.set(st.position_size)
        ph = ta.pivothigh(self.high, self.pivot_left, self.pivot_right)
        pl = ta.pivotlow(self.low, self.pivot_left, self.pivot_right)
        if not na(ph):
            self.resistance = ph
        if not na(pl):
            self.support = pl
        avg_volume = ta.sma(self.volume, self.vol_length)
        volume_surge = self.volume > avg_volume * self.vol_multiplier
        ema_val = ta.ema(self.close, self.ema_length)
        trend_up_ok = (not self.use_trend_filter) or self.close > ema_val
        trend_down_ok = (not self.use_trend_filter) or self.close < ema_val
        atr_val = ta.atr(self.atr_length)
        in_range = self.time >= self.start_date and self.time <= self.end_date
        long_breakout = (not na(self.resistance)) and ta.crossover(self.close, self.resistance) and volume_surge and trend_up_ok and in_range
        short_breakout = (not na(self.support)) and ta.crossunder(self.close, self.support) and volume_surge and trend_down_ok and in_range
        if long_breakout:
            st.entry("Long", st.long)
            if self.use_struct_stop and not na(self.support):
                self.long_stop_price = self.support - atr_val * self.stop_buffer_atr
            else:
                self.long_stop_price = self.close - atr_val * self.atr_stop_mult
            self.long_tgt_price = self.close + atr_val * self.atr_target_mult
        if short_breakout:
            st.entry("Short", st.short)
            if self.use_struct_stop and not na(self.resistance):
                self.short_stop_price = self.resistance + atr_val * self.stop_buffer_atr
            else:
                self.short_stop_price = self.close + atr_val * self.atr_stop_mult
            self.short_tgt_price = self.close - atr_val * self.atr_target_mult
        if st.position_size > 0:
            st.exit("Long Exit", "Long", stop=self.long_stop_price, limit=self.long_tgt_price)
        if st.position_size < 0:
            st.exit("Short Exit", "Short", stop=self.short_stop_price, limit=self.short_tgt_price)
        flat_now = st.position_size == 0
        flat_prev = (not na(pos_1)) and pos_1 != 0
        if flat_now and flat_prev:
            self.long_stop_price = NA
            self.long_tgt_price = NA
            self.short_stop_price = NA
            self.short_tgt_price = NA
        self.plot(self.resistance, "Resistance", color=color.red, style="linebr")
        self.plot(self.support, "Support", color=color.teal, style="linebr")
        self.plot(ema_val if self.use_trend_filter else NA, "EMA Trend", color=color.gray)

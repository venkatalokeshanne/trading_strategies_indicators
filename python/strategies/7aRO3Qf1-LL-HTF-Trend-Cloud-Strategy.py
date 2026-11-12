"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : L&L HTF Trend Cloud Strategy
Author       : L&L Capital
Source URL   : https://www.tradingview.com/script/7aRO3Qf1
Pine version : v6
Licence      : Mozilla Public License 2.0
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). On the higher timeframe (auto-mapped from the chart period, or a manual one) a trend line (EMA13) and an ATR cloud (EMA8 of the true range x a mode-dependent percentage) set a direction: up when the HTF close is above trend + ATR,
down when below trend - ATR, otherwise unchanged; a direction change opens a long / short (optionally only with the EMA8/13/21/34 stack and the close on the right side of the trend line), and the trade is closed when the chart close goes through the cloud line against the direction.
An optional percent stop / target is issued from the average entry price.
Deviations from the original: none (a never-initialised stop-line branch is reproduced as written).
Not carried over: the trend / cloud plots and fill, signal shapes, alert messages and the info table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, ta

AUTO_TF = {"1": "5", "2": "5", "3": "5", "4": "5", "5": "30", "10": "30", "15": "30", "30": "240", "60": "240", "120": "240", "180": "D",
           "240": "D", "D": "W", "W": "M", "M": "3M"}
ATR_LEN = {"Tight": 60, "Normal": 80, "Loose": 100, "FOMC": 120, "Net": 140}


class LlHtfTrendCloud(Script):
    TITLE = "L&L HTF Trend Cloud Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "7aRO3Qf1", "author": "L&L Capital", "licence": "Mozilla Public License 2.0", "url": "https://www.tradingview.com/script/7aRO3Qf1"}

    def init(self):
        i = self.input
        g = "Trading Parameters"
        self.stop_loss_pct = i.float(1.0, "Stop Loss (%)", minval=0.1, step=0.1, group=g)
        self.take_profit_pct = i.float(2.0, "Take Profit (%)", minval=0.1, step=0.1, group=g)
        self.use_cloud_exit = i.bool(True, "Use Cloud Exit", group=g)
        self.use_sltp = i.bool(False, "Use Stop Loss & Take Profit", group=g)
        self.pyramiding_qty = i.int(1, "Pyramiding Quantity", minval=1, step=1, group=g)
        g = "HTF Settings"
        self.trend_mode = i.string("Normal", "Trend Mode", options=["Tight", "Normal", "Loose", "FOMC", "Net"], group=g)
        self.htf_mode = i.string("Auto", "HTF Mode", options=["Auto", "Manual"], group=g)
        self.tf_manual = i.timeframe("60", "HTF Aggregation (Manual)", group=g)
        g = "Signal Settings"
        self.require_alignment = i.bool(True, "Require Trend Alignment", group=g)
        self.entry_signal = i.string("Both", "Entry Signal", options=["Both", "Bullish Only", "Bearish Only"], group=g)
        self.stop_line = NA

    def on_bar(self):
        st = self.strategy
        close = self.close
        tf_auto = AUTO_TF.get(self.timeframe.period, self.timeframe.period)
        tf = tf_auto if self.htf_mode == "Auto" else self.tf_manual
        ema8 = self.security(None, tf, lambda v: ta.ema(v.close, 8))
        ema13 = self.security(None, tf, lambda v: ta.ema(v.close, 13))
        ema21 = self.security(None, tf, lambda v: ta.ema(v.close, 21))
        ema34 = self.security(None, tf, lambda v: ta.ema(v.close, 34))
        ema_up = ema8 > ema13 and ema13 > ema21 and ema21 > ema34
        ema_down = ema8 < ema13 and ema13 < ema21 and ema21 < ema34
        trend = self.security(None, tf, lambda v: ta.ema(v.close, 13))
        close_htf = self.security(None, tf, lambda v: v.close)
        atr_len = ATR_LEN[self.trend_mode]
        atr_htf = self.security(None, tf, lambda v: ta.ema(ta.tr(True), 8))
        atr_value = (atr_len / 100) * atr_htf
        is_up = close_htf > (trend + atr_value)
        is_down = close_htf < (trend - atr_value)
        sd_h = self.H("stop_direction")
        sd_1 = sd_h[1]
        stop_direction = 1.0 if is_up else (-1.0 if is_down else sd_1)
        sd_h.set(stop_direction)
        if stop_direction == 1:
            self.stop_line = trend - atr_value
        elif stop_direction == -1:
            self.stop_line = trend + atr_value
        else:
            self.stop_line = sd_1
        bullish_cross = stop_direction == 1 and sd_1 == -1
        bearish_cross = stop_direction == -1 and sd_1 == 1
        trend_is_bullish = bool(ema_up and close_htf >= trend)
        trend_is_bearish = bool(ema_down and close_htf <= trend)
        if self.require_alignment:
            long_condition = bool(bullish_cross and trend_is_bullish)
            short_condition = bool(bearish_cross and trend_is_bearish)
        else:
            long_condition = bool(bullish_cross)
            short_condition = bool(bearish_cross)
        if self.entry_signal == "Bullish Only":
            short_condition = False
        elif self.entry_signal == "Bearish Only":
            long_condition = False
        long_exit_cloud = bool(close < self.stop_line and stop_direction == 1)
        short_exit_cloud = bool(close > self.stop_line and stop_direction == -1)
        avg = st.position_avg_price
        pos = st.position_size
        if long_condition:
            st.entry("Long", st.long, qty=self.pyramiding_qty)
        if short_condition:
            st.entry("Short", st.short, qty=self.pyramiding_qty)
        if long_exit_cloud and pos > 0:
            st.close("Long", comment="Cloud Exit Long")
        if short_exit_cloud and pos < 0:
            st.close("Short", comment="Cloud Exit Short")
        if self.use_sltp:
            if pos > 0:
                st.exit("Long Exit", "Long", stop=avg * (1 - self.stop_loss_pct / 100), limit=avg * (1 + self.take_profit_pct / 100))
            if pos < 0:
                st.exit("Short Exit", "Short", stop=avg * (1 + self.stop_loss_pct / 100), limit=avg * (1 - self.take_profit_pct / 100))

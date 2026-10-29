"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EMA Ribbon Fan Angle Strategy (Gradient Ribbon | EMA Ribbon Slope-Acceleration System)
Author       : blitz_locked
Source URL   : https://www.tradingview.com/script/X0F9OE4L-Gradient-Ribbon-EMA-Ribbon-Slope-Acceleration-System
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Five EMAs (8/13/21/34/55) are each turned into a percent slope over the lookback; when all slopes point the same way and fan out in order (fastest steepest), the
fastest-minus-slowest slope ("fan score") beyond the entry threshold, RSI in its band and volume above average open a position when flat, risk-sized by an ATR stop with an R-multiple target
placed with the entry. A fan that stops widening (or a fan score under the exit threshold) closes the trade at the next open.

Deviations from the original: none.
Not carried over: the ribbon plots and gradient fill, signal backgrounds and the hidden fan-score plot (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, ta


class EmaRibbonFan(Script):
    TITLE = "EMA Ribbon Fan Angle Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="fixed", default_qty_value=1, commission_type="percent", commission_value=0.05, slippage=1)
    SOURCE = {"id": "X0F9OE4L", "author": "blitz_locked", "licence": "not stated",
              "url": "https://www.tradingview.com/script/X0F9OE4L-Gradient-Ribbon-EMA-Ribbon-Slope-Acceleration-System"}

    def init(self):
        g = "Ribbon"
        self.len8 = self.input.int(8, "Fastest EMA", group=g)
        self.len13 = self.input.int(13, "EMA 2", group=g)
        self.len21 = self.input.int(21, "EMA 3", group=g)
        self.len34 = self.input.int(34, "EMA 4", group=g)
        self.len55 = self.input.int(55, "Slowest EMA", group=g)
        g = "Fan Angle"
        self.slope_lookback = self.input.int(5, "Slope lookback (bars)", group=g)
        self.fan_enter_thresh = self.input.float(0.8, "Fan expansion entry threshold (%)", group=g, step=0.1)
        self.fan_exit_thresh = self.input.float(0.2, "Fan compression exit threshold (%)", group=g, step=0.1)
        g = "Confirmation"
        self.rsi_len = self.input.int(14, "RSI length", group=g)
        self.rsi_min = self.input.float(50, "RSI min (bullish floor / bearish ceiling mirror)", group=g)
        self.rsi_max = self.input.float(70, "RSI max (avoid overbought/oversold extremes)", group=g)
        self.vol_len = self.input.int(20, "Volume average length", group=g)
        self.vol_mult = self.input.float(1.0, "Volume must exceed avg x this", group=g, step=0.1)
        g = "Risk"
        self.risk_pct = self.input.float(1.0, "Risk per trade (% of equity)", group=g, step=0.1)
        self.atr_len = self.input.int(14, "ATR length", group=g)
        self.atr_mult = self.input.float(2.0, "ATR stop multiple", group=g, step=0.1)
        self.r_multiple = self.input.float(2.0, "Take profit (R multiple)", group=g, step=0.1)

    def _slope(self, tag, value):
        h = self.H(tag)
        past = h[self.slope_lookback]
        h.set(value)
        return div(value - past, past) * 100

    def on_bar(self):
        ema8 = ta.ema(self.close, self.len8)
        ema13 = ta.ema(self.close, self.len13)
        ema21 = ta.ema(self.close, self.len21)
        ema34 = ta.ema(self.close, self.len34)
        ema55 = ta.ema(self.close, self.len55)
        s8 = self._slope("e8", ema8)
        s13 = self._slope("e13", ema13)
        s21 = self._slope("e21", ema21)
        s34 = self._slope("e34", ema34)
        s55 = self._slope("e55", ema55)
        all_positive = s8 > 0 and s13 > 0 and s21 > 0 and s34 > 0 and s55 > 0
        increasing_fan_up = s8 > s13 and s13 > s21 and s21 > s34 and s34 > s55
        fanning_open_up = all_positive and increasing_fan_up
        all_negative = s8 < 0 and s13 < 0 and s21 < 0 and s34 < 0 and s55 < 0
        increasing_fan_down = s8 < s13 and s13 < s21 and s21 < s34 and s34 < s55
        fanning_open_down = all_negative and increasing_fan_down
        fan_score = s8 - s55
        rsi = ta.rsi(self.close, self.rsi_len)
        rsi_ok_long = rsi > self.rsi_min and rsi < self.rsi_max
        rsi_ok_short = rsi < (100 - self.rsi_min) and rsi > (100 - self.rsi_max)
        avg_vol = ta.sma(self.volume, self.vol_len)
        vol_ok = self.volume > avg_vol * self.vol_mult
        st = self.strategy
        long_condition = fanning_open_up and fan_score > self.fan_enter_thresh and rsi_ok_long and vol_ok and st.position_size == 0
        short_condition = fanning_open_down and fan_score < -self.fan_enter_thresh and rsi_ok_short and vol_ok and st.position_size == 0
        exit_long_condition = (not increasing_fan_up) or (fan_score < self.fan_exit_thresh)
        exit_short_condition = (not increasing_fan_down) or (fan_score > -self.fan_exit_thresh)
        atr_val = ta.atr(self.atr_len)
        stop_distance = atr_val * self.atr_mult
        if long_condition:
            risk_amount = st.equity * (self.risk_pct / 100)
            qty = div(risk_amount, stop_distance)
            entry_price = float(self.close)
            st.entry("Long", st.long, qty=qty)
            st.exit("Exit Long", "Long", stop=entry_price - stop_distance, limit=entry_price + stop_distance * self.r_multiple)
        if short_condition:
            risk_amount = st.equity * (self.risk_pct / 100)
            qty = div(risk_amount, stop_distance)
            entry_price = float(self.close)
            st.entry("Short", st.short, qty=qty)
            st.exit("Exit Short", "Short", stop=entry_price + stop_distance, limit=entry_price - stop_distance * self.r_multiple)
        if exit_long_condition and st.position_size > 0:
            st.close("Long", comment="Fan compression")
        if exit_short_condition and st.position_size < 0:
            st.close("Short", comment="Fan compression")
        self.plot(ema8, "EMA 8", color=color.lime)
        self.plot(ema55, "EMA 55", color=color.red)

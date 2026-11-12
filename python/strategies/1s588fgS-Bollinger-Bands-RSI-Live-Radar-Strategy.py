"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : TrenchWrld BB + RSI Live Radar Strategy
Author       : atreynolds19
Source URL   : https://www.tradingview.com/script/1s588fgS-Bollinger-Bands-RSI-Live-Radar-Strategy
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. While flat, a Bollinger-band touch (close beyond the band with the RSI at the oversold / overbought level) or reclaim (previous close outside the band,
the close back inside, RSI past its level) opens a long / short, optionally only on the right side of the 200 EMA. A percentage stop / take-profit bracket around the average price
is issued once the position exists and works from the next bar.

Deviations from the original: none.
Not carried over: the live-watch markers, the setup-radar table, trade-line plots and alerts (display only; calc_on_every_tick has no effect on historical bars).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, ta


class TrenchWrldBbRsi(Script):
    TITLE = "TrenchWrld BB + RSI Live Radar Strategy"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=10, commission_type="percent", commission_value=0.06, pyramiding=0)
    SOURCE = {"id": "1s588fgS", "author": "atreynolds19", "licence": "not stated",
              "url": "https://www.tradingview.com/script/1s588fgS-Bollinger-Bands-RSI-Live-Radar-Strategy"}

    def init(self):
        self.bb_length = self.input.int(20, "Bollinger Band Length", minval=1)
        self.bb_mult = self.input.float(2.0, "Bollinger Band Multiplier", step=0.1)
        self.rsi_length = self.input.int(14, "RSI Length", minval=1)
        self.rsi_oversold = self.input.float(30.0, "RSI Oversold Level", step=0.5)
        self.rsi_overbought = self.input.float(70.0, "RSI Overbought Level", step=0.5)
        self.trade_mode = self.input.string("Both", "Trade Mode", options=["Long Only", "Short Only", "Both"])
        self.entry_style = self.input.string("Reclaim Band", "Entry Style", options=["Touch Band", "Reclaim Band"])
        self.take_profit_pct = self.input.float(3.0, "Take Profit %", step=0.1, minval=0.1)
        self.stop_loss_pct = self.input.float(1.5, "Stop Loss %", step=0.1, minval=0.1)
        self.use_trend_filter = self.input.bool(True, "Use 200 EMA Trend Filter")
        self.ema_length = self.input.int(200, "EMA Length", minval=1)

    def on_bar(self):
        st = self.strategy
        basis = ta.sma(self.close, self.bb_length)
        dev = self.bb_mult * ta.stdev(self.close, self.bb_length)
        upper_band = basis + dev
        lower_band = basis - dev
        rsi = ta.rsi(self.close, self.rsi_length)
        ema = ta.ema(self.close, self.ema_length)
        up_h, lo_h = self.H("up"), self.H("lo")
        upper_1, lower_1 = up_h[1], lo_h[1]
        up_h.set(upper_band)
        lo_h.set(lower_band)
        close_1 = self.close[1]
        bull_trend = self.close > ema
        bear_trend = self.close < ema
        long_trend_allowed = (not self.use_trend_filter) or bull_trend
        short_trend_allowed = (not self.use_trend_filter) or bear_trend
        allow_long = self.trade_mode == "Long Only" or self.trade_mode == "Both"
        allow_short = self.trade_mode == "Short Only" or self.trade_mode == "Both"
        long_touch = self.close <= lower_band and rsi <= self.rsi_oversold
        short_touch = self.close >= upper_band and rsi >= self.rsi_overbought
        long_reclaim = close_1 < lower_1 and self.close > lower_band and rsi > self.rsi_oversold
        short_reclaim = close_1 > upper_1 and self.close < upper_band and rsi < self.rsi_overbought
        long_signal = long_touch if self.entry_style == "Touch Band" else long_reclaim
        short_signal = short_touch if self.entry_style == "Touch Band" else short_reclaim
        enter_long = allow_long and long_signal and long_trend_allowed and st.position_size == 0
        enter_short = allow_short and short_signal and short_trend_allowed and st.position_size == 0
        if enter_long:
            st.entry("Long", st.long)
        if enter_short:
            st.entry("Short", st.short)
        entry_price = st.position_avg_price
        long_take_profit = entry_price * (1 + self.take_profit_pct / 100)
        long_stop_loss = entry_price * (1 - self.stop_loss_pct / 100)
        short_take_profit = entry_price * (1 - self.take_profit_pct / 100)
        short_stop_loss = entry_price * (1 + self.stop_loss_pct / 100)
        if st.position_size > 0:
            st.exit("Long TP/SL", from_entry="Long", limit=long_take_profit, stop=long_stop_loss)
        if st.position_size < 0:
            st.exit("Short TP/SL", from_entry="Short", limit=short_take_profit, stop=short_stop_loss)
        self.plot(basis, "BB Basis", color=color.gray)
        self.plot(upper_band, "Upper Bollinger Band", color=color.blue)
        self.plot(lower_band, "Lower Bollinger Band", color=color.blue)
        self.plot(ema, "EMA Trend Filter", color=color.orange, linewidth=2)

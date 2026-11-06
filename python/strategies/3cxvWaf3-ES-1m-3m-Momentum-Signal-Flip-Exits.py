"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : ES 3m Momentum - Signal Flip Exits
Author       : BuckDiesel
Source URL   : https://www.tradingview.com/script/3cxvWaf3-ES-1m-3m-Momentum-Signal-Flip-Exits
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. An EMA8 / EMA21 cross in the direction of EMA50, a smoothed RSI side, a MACD(8, 21, 3) side and above-average volume inside the 08:30-15:00
Chicago session flips the position at the next open. While a position exists a 1-point limit target around position_avg_price is issued (so it first works one bar after the fill); everything
is closed on bars that start in the 15:00-15:05 Chicago window.

Deviations from the original: `time(...) != 0` is written as "inside the session" (an na result from time() makes the Pine comparison false, which Python's NaN != 0 would get wrong).
Not carried over: EMA plots, signal shapes and bar colouring (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, na, ta


class EsMomentum(Script):
    TITLE = "ES 3m Momentum - Signal Flip Exits"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=1, commission_type="cash_per_contract", commission_value=2.50,
                    slippage=1, margin_long=500, margin_short=500)
    SOURCE = {"id": "3cxvWaf3", "author": "BuckDiesel", "licence": "not stated",
              "url": "https://www.tradingview.com/script/3cxvWaf3-ES-1m-3m-Momentum-Signal-Flip-Exits"}

    def init(self):
        self.ema_fast = self.input.int(8, "Fast EMA", minval=1)
        self.ema_slow = self.input.int(21, "Slow EMA", minval=1)
        self.ema_filter = self.input.int(50, "Trend Filter EMA", minval=1)
        self.rsi_len = self.input.int(14, "RSI Length", minval=2)
        self.rsi_smooth = self.input.int(3, "RSI Smooth", minval=1)
        self.vol_mult = self.input.float(1.2, "Min Volume vs MA mult", step=0.1)
        self.vol_len = self.input.int(20, "Volume MA Length", minval=5)
        self.trade_dir = self.input.string("Both", "Direction", options=["Long", "Short", "Both"])
        self.rth_only = self.input.bool(True, "RTH only (08:30–15:00 CT)")
        self.tp_pt = self.input.float(1.0, "Partial TP points (0 = off)", step=0.25, minval=0)

    def on_bar(self):
        in_rth = (not self.rth_only) or (not na(self.time_fn(None, "0830-1500", "America/Chicago")))
        fast = ta.ema(self.close, self.ema_fast)
        slow = ta.ema(self.close, self.ema_slow)
        trend = ta.ema(self.close, self.ema_filter)
        rsi_raw = ta.rsi(self.close, self.rsi_len)
        rsi = ta.ema(rsi_raw, self.rsi_smooth)
        vol_ma = ta.sma(self.volume, self.vol_len)
        macd_line, signal_line, _ = ta.macd(self.close, self.ema_fast, self.ema_slow, self.rsi_smooth)
        macd_bull = macd_line > signal_line
        macd_bear = macd_line < signal_line
        above_trend = self.close > trend
        below_trend = self.close < trend
        rsi_long = rsi > 50
        rsi_short = rsi < 50
        vol_ok = self.volume > vol_ma * self.vol_mult
        long_entry = ta.crossover(fast, slow) and above_trend and rsi_long and macd_bull and vol_ok and in_rth
        short_entry = ta.crossunder(fast, slow) and below_trend and rsi_short and macd_bear and vol_ok and in_rth
        st = self.strategy
        if long_entry and (self.trade_dir == "Long" or self.trade_dir == "Both"):
            st.close("Short", comment="Flip→Long")
            st.entry("Long", st.long)
        if short_entry and (self.trade_dir == "Short" or self.trade_dir == "Both"):
            st.close("Long", comment="Flip→Short")
            st.entry("Short", st.short)
        if self.tp_pt > 0:
            if st.position_size > 0:
                st.exit("Long TP", "Long", limit=st.position_avg_price + self.tp_pt)
            if st.position_size < 0:
                st.exit("Short TP", "Short", limit=st.position_avg_price - self.tp_pt)
        if self.rth_only and not na(self.time_fn(None, "1500-1505", "America/Chicago")):
            st.close_all(comment="EOD")
        self.plot(fast, "EMA 8", color=color.aqua)
        self.plot(slow, "EMA 21", color=color.orange, linewidth=2)
        self.plot(trend, "EMA 50", color=color.gray, linewidth=2)

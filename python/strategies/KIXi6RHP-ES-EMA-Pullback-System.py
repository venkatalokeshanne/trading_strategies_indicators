"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : ES EMA Pullback System
Author       : cdeck1027
Source URL   : https://www.tradingview.com/script/KIXi6RHP-ES-EMA-Pullback-System
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The session input "0930-1130,1330-1600" has two ranges; a bar is in the
session when its start time is inside either one (exchange time zone). strategy.exit is
unconditional, re-issued every bar with that bar's ATR levels, so bar i works with bar i-1's levels
(also on the fill bar).

Deviations from the original: none.
Not carried over: the SELL labels (label.new, never read back).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, na, ta


class EsEmaPullbackSystem(Script):
    TITLE = "ES EMA Pullback System"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=50000, default_qty_type="fixed", default_qty_value=1)
    SOURCE = {"id": "KIXi6RHP", "author": "cdeck1027", "licence": "not stated",
              "url": "https://www.tradingview.com/script/KIXi6RHP-ES-EMA-Pullback-System"}

    def init(self):
        self.fast_ema = self.input.int(9)
        self.mid_ema = self.input.int(21)
        self.slow_ema = self.input.int(50)
        self.atr_len = self.input.int(14)
        self.stop_atr = self.input.float(1.6)
        self.target_atr = self.input.float(3.2)
        self.session_input = self.input.session("0930-1130,1330-1600")

    def on_bar(self):
        in_session = not na(self.time_fn(None, self.session_input))
        ema9 = ta.ema(self.close, self.fast_ema)
        ema21 = ta.ema(self.close, self.mid_ema)
        ema50 = ta.ema(self.close, self.slow_ema)
        self.plot(ema9, color=color.blue)
        self.plot(ema21, color=color.orange)
        self.plot(ema50, color=color.red)
        bear_trend = ema9 < ema21 and ema21 < ema50
        pullback = self.high >= ema9
        bear_momentum = self.close < self.open
        sell_signal = bear_trend and pullback and bear_momentum
        atr = ta.atr(self.atr_len)
        short_stop = self.close + atr * self.stop_atr
        short_target = self.close - atr * self.target_atr
        st = self.strategy
        if sell_signal and in_session:
            st.entry("SELL", st.short)
        st.exit("EXIT", "SELL", stop=short_stop, limit=short_target)

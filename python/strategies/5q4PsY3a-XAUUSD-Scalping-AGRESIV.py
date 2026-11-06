"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : XAUUSD Scalping V2 AGRESIV
Author       : Andra2525
Source URL   : https://www.tradingview.com/script/5q4PsY3a-XAUUSD-Scalping-AGRESIV
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The bracket is placed with the entry on the signal bar, so it works from the
fill bar. trail_points is given without a trail_offset, which in Pine never trails; the fixed stop and
target are what act (same as the other trail_points-only scripts in this repo).

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, ta


class XauusdScalpingAgresiv(Script):
    TITLE = "XAUUSD Scalping V2 AGRESIV"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "5q4PsY3a", "author": "Andra2525", "licence": "not stated",
              "url": "https://www.tradingview.com/script/5q4PsY3a-XAUUSD-Scalping-AGRESIV"}

    def init(self):
        self.ema_fast_len = self.input.int(5, "EMA Rapid")
        self.ema_slow_len = self.input.int(13, "EMA Lent")
        self.rsi_len = self.input.int(7, "RSI Rapid")
        self.atr_len = self.input.int(14, "ATR Length")
        self.tp_atr = self.input.float(1.2, "Take Profit (ATR multiplu)")
        self.sl_atr = self.input.float(0.8, "Stop Loss (ATR multiplu)")
        self.trail_atr = self.input.float(0.5, "Trailing Stop (ATR multiplu)")
        self.min_volatility = self.input.float(0.5, "Filtru volatilitate (ATR minim)")

    def on_bar(self):
        ema_fast = ta.ema(self.close, self.ema_fast_len)
        ema_slow = ta.ema(self.close, self.ema_slow_len)
        rsi = ta.rsi(self.close, self.rsi_len)
        atr = ta.atr(self.atr_len)
        volatility_ok = atr > self.min_volatility
        cross_up = ta.crossover(ema_fast, ema_slow)
        cross_dn = ta.crossunder(ema_fast, ema_slow)
        long_condition = cross_up and rsi > 55 and volatility_ok
        short_condition = cross_dn and rsi < 45 and volatility_ok
        st = self.strategy
        if long_condition:
            entry_price = self.close
            take_profit = entry_price + atr * self.tp_atr
            stop_loss = entry_price - atr * self.sl_atr
            st.entry("BUY", st.long)
            st.exit("TP/SL BUY", from_entry="BUY", limit=take_profit, stop=stop_loss,
                    trail_points=div(atr * self.trail_atr, self.syminfo.mintick))
        if short_condition:
            entry_price = self.close
            take_profit = entry_price - atr * self.tp_atr
            stop_loss = entry_price + atr * self.sl_atr
            st.entry("SELL", st.short)
            st.exit("TP/SL SELL", from_entry="SELL", limit=take_profit, stop=stop_loss,
                    trail_points=div(atr * self.trail_atr, self.syminfo.mintick))
        self.plot(ema_fast, color=color.green)
        self.plot(ema_slow, color=color.red)
        self.plotshape(long_condition)
        self.plotshape(short_condition)

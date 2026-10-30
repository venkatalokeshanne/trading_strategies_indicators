"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : NQ SCALP FIX + SIGNALS
Author       : ColasBreugnon
Source URL   : https://www.tradingview.com/script/1B4vXkpF
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. EMA 5/24/150 stacked, price crossing the fast EMA and RSI beyond 55/45 enters when flat; the
ATR stop (1.5) and target (2.5) are rebuilt every bar from the position average price and issued only while a position
exists, so they first work on the bar after the fill.

Deviations from the original: none.
Not carried over: signal shapes, bar colouring and the extra 600-EMA plot (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, ta


class NqScalpFix(Script):
    TITLE = "NQ SCALP FIX + SIGNALS"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0)
    SOURCE = {"id": "1B4vXkpF", "author": "ColasBreugnon", "licence": "not stated",
              "url": "https://www.tradingview.com/script/1B4vXkpF"}

    def init(self):
        self.ema_fast = self.input.int(5, "ema_fast")
        self.ema_mid = self.input.int(24, "ema_mid")
        self.ema_slow = self.input.int(150, "ema_slow")
        self.rsi_len = self.input.int(14, "rsi_len")
        self.rsi_bull = self.input.int(55, "rsi_bull")
        self.rsi_bear = self.input.int(45, "rsi_bear")
        self.atr_len = self.input.int(14, "atr_len")
        self.sl_atr = self.input.float(1.5, "sl_atr")
        self.tp_atr = self.input.float(2.5, "tp_atr")
        self.len = self.input.int(600, "Length", minval=1)
        self.src = self.input.source(self.close, "Source")

    def on_bar(self):
        e_fast = ta.ema(self.close, self.ema_fast)
        e_mid = ta.ema(self.close, self.ema_mid)
        e_slow = ta.ema(self.close, self.ema_slow)
        rsi = ta.rsi(self.close, self.rsi_len)
        atr = ta.atr(self.atr_len)
        bull = e_fast > e_mid and e_mid > e_slow
        bear = e_fast < e_mid and e_mid < e_slow
        long_cond = bull and ta.crossover(self.close, e_fast) and rsi > self.rsi_bull
        short_cond = bear and ta.crossunder(self.close, e_fast) and rsi < self.rsi_bear
        st = self.strategy
        if long_cond and st.position_size == 0:
            st.entry("L", st.long)
        if short_cond and st.position_size == 0:
            st.entry("S", st.short)
        if st.position_size > 0:
            st.exit("L EXIT", "L", stop=st.position_avg_price - atr * self.sl_atr, limit=st.position_avg_price + atr * self.tp_atr)
        if st.position_size < 0:
            st.exit("S EXIT", "S", stop=st.position_avg_price + atr * self.sl_atr, limit=st.position_avg_price - atr * self.tp_atr)
        out = ta.ema(self.src, self.len)
        self.plot(e_fast, color=color.aqua)
        self.plot(e_mid, color=color.orange)
        self.plot(e_slow, color=color.purple)
        self.plot(out, "EMA", color=color.blue)

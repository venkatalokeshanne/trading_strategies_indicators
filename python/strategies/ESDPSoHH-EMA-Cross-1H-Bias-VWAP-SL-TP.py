"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EMA Cross + 1H Bias + VWAP SL/TP
Author       : Stef_trades1
Source URL   : https://www.tradingview.com/script/ESDPSoHH-EMA-Cross-1H-Bias-VWAP-SL-TP
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. request.security(..., "60", ...) runs with lookahead off (pinelib
security): on a lower-timeframe chart a 60-minute bar's value shows on the LAST chart bar of that
hour; earlier chart bars of the hour show the previous hour's value. Stop = VWAP at the signal
bar, target = the same distance on the other side of the close, bracket placed with the entry.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color, ta


class EmaCross1hBiasVwap(Script):
    TITLE = "EMA Cross + 1H Bias + VWAP SL/TP"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "ESDPSoHH", "author": "Stef_trades1", "licence": "not stated",
              "url": "https://www.tradingview.com/script/ESDPSoHH-EMA-Cross-1H-Bias-VWAP-SL-TP"}

    def init(self):
        self.ema_fast_len = self.input.int(10, "Fast EMA")
        self.ema_slow_len = self.input.int(20, "Slow EMA")
        self.ema_htf_len = self.input.int(20, "HTF EMA (1H)")

    def on_bar(self):
        fast_ema = ta.ema(self.close, self.ema_fast_len)
        slow_ema = ta.ema(self.close, self.ema_slow_len)
        htf_close = self.security(None, "60", lambda v: v.close)
        htf_ema = self.security(None, "60", lambda v: ta.ema(v.close, self.ema_htf_len))
        vwap = ta.vwap(self.close)
        bull_htf = htf_close > htf_ema
        bear_htf = htf_close < htf_ema
        long_condition = ta.crossover(fast_ema, slow_ema)
        short_condition = ta.crossunder(fast_ema, slow_ema)
        long_final = long_condition and bull_htf and self.close > vwap
        short_final = short_condition and bear_htf and self.close < vwap
        long_sl = vwap
        short_sl = vwap
        long_tp = self.close + (self.close - long_sl)
        short_tp = self.close - (short_sl - self.close)
        st = self.strategy
        if long_final:
            st.entry("Long", st.long)
            st.exit("Long TP/SL", from_entry="Long", stop=long_sl, limit=long_tp)
        if short_final:
            st.entry("Short", st.short)
            st.exit("Short TP/SL", from_entry="Short", stop=short_sl, limit=short_tp)
        self.plot(fast_ema, color=color.orange)
        self.plot(slow_ema, color=color.blue)
        self.plot(htf_ema, color=color.purple)
        self.plot(vwap, color=color.fuchsia)

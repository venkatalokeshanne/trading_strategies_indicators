"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EMA DMI MACD RSI Strategy
Author       : bhajneek12
Source URL   : https://www.tradingview.com/script/z39XLJR2-EMA-DMI-MACD-RSI-Strategy
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The hourly EMA50 comes from request.security with lookahead off (a
60-minute bar's value shows on the last chart bar of that hour, earlier bars show the previous hour).
The two strategy.exit calls are unconditional and use the current bar's close and ATR, so bar i works
with bar i-1's levels (also on the fill bar).

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class EmaDmiMacdRsi(Script):
    TITLE = "EMA DMI MACD RSI Strategy"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "z39XLJR2", "author": "bhajneek12", "licence": "not stated",
              "url": "https://www.tradingview.com/script/z39XLJR2-EMA-DMI-MACD-RSI-Strategy"}

    def on_bar(self):
        ema5 = ta.ema(self.close, 5)
        ema13 = ta.ema(self.close, 13)
        ema26 = ta.ema(self.close, 26)
        ema200 = ta.ema(self.close, 200)
        self.plot(ema5, color=color.green)
        self.plot(ema13, color=color.orange)
        self.plot(ema26, color=color.red)
        self.plot(ema200, color=color.blue)
        rsi_value = ta.rsi(self.close, 14)
        macd_line, signal_line, hist_line = ta.macd(self.close, 12, 26, 9)
        plus_di, minus_di, adx_value = ta.dmi(14, 14)
        volume_ma = ta.sma(self.volume, 20)
        high_volume = self.volume > volume_ma
        htf_ema = self.security(None, "60", lambda v: ta.ema(v.close, 50))
        atr_value = ta.atr(14)
        buy_signal = (ema5 > ema13 and ema13 > ema26 and self.close > ema200 and macd_line > signal_line
                      and rsi_value > 55 and plus_di > minus_di and adx_value > 20 and high_volume
                      and self.close > htf_ema)
        sell_signal = (ema5 < ema13 and ema13 < ema26 and self.close < ema200 and macd_line < signal_line
                       and rsi_value < 45 and minus_di > plus_di and adx_value > 20 and high_volume
                       and self.close < htf_ema)
        st = self.strategy
        if buy_signal:
            st.entry("BUY", st.long)
        if sell_signal:
            st.entry("SELL", st.short)
        st.exit("BUY EXIT", from_entry="BUY", stop=self.close - atr_value * 1.5, limit=self.close + atr_value * 3)
        st.exit("SELL EXIT", from_entry="SELL", stop=self.close + atr_value * 1.5, limit=self.close - atr_value * 3)
        self.plotshape(buy_signal, title="BUY")
        self.plotshape(sell_signal, title="SELL")

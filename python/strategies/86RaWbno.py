"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : SMA Strategy
Author       : ColasBreugnon
Source URL   : https://www.tradingview.com/script/86RaWbno
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. SMA5 crossing SMA9 enters with a 5-bar swing stop and a 2R target, only when
the risk is larger than one tick; the bracket is placed with the entry. The highest / lowest calls inside
the signal blocks, so each call site only sees the lows / highs of the bars it ran on (LESSONS P5): the
5-value window is the last five SIGNAL bars, not the last five chart bars, and the first four signals of
each kind therefore have no stop level and enter nothing (risk is na). If TradingView evaluates
ta.lowest / ta.highest over the real price history instead, early trades would differ.

Deviations from the original: none.
Not carried over: the barcolor() colouring and plot styles (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class SmaStrategy(Script):
    TITLE = "SMA Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0)
    SOURCE = {"id": "86RaWbno", "author": "ColasBreugnon", "licence": "not stated",
              "url": "https://www.tradingview.com/script/86RaWbno"}

    def on_bar(self):
        sma5 = ta.sma(self.close, 5)
        sma9 = ta.sma(self.close, 9)
        sma20 = ta.sma(self.close, 20)
        sma50 = ta.sma(self.close, 50)
        sma200 = ta.sma(self.close, 200)
        long_signal = ta.crossover(sma5, sma9)
        short_signal = ta.crossunder(sma5, sma9)
        st = self.strategy
        if long_signal:
            sl = ta.lowest(self.low, 5)
            risk = self.close - sl
            if risk > self.syminfo.mintick:
                tp = self.close + risk * 2
                st.entry("LONG", st.long)
                st.exit("LONG EXIT", from_entry="LONG", stop=sl, limit=tp)
        if short_signal:
            sl = ta.highest(self.high, 5)
            risk = sl - self.close
            if risk > self.syminfo.mintick:
                tp = self.close - risk * 2
                st.entry("SHORT", st.short)
                st.exit("SHORT EXIT", from_entry="SHORT", stop=sl, limit=tp)
        self.plot(sma9, color=color.rgb(120, 123, 134, 49))
        self.plot(sma20, color=color.rgb(255, 153, 0, 60))
        self.plot(sma50, color=color.rgb(172, 0, 0, 54))
        self.plot(sma200, color=color.rgb(0, 110, 255, 47))
        self.plotshape(long_signal, title="BUY")
        self.plotshape(short_signal, title="SELL")

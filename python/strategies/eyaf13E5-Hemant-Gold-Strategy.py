"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Hemant Gold Strategy
Author       : rupasgavane
Source URL   : https://www.tradingview.com/script/eyaf13E5-Hemant-Gold-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Both strategy.exit calls are unconditional and use the CURRENT position's
average price (na while flat) for both directions' levels, as written, so on a reversal the new
position's first bar still works with the old position's average price.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color, ta


class HemantGold(Script):
    TITLE = "Hemant Gold Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, pyramiding=0, commission_type="percent", commission_value=0.01)
    SOURCE = {"id": "eyaf13E5", "author": "rupasgavane", "licence": "not stated",
              "url": "https://www.tradingview.com/script/eyaf13E5-Hemant-Gold-Strategy"}

    def init(self):
        self.ema_len = self.input.int(200, "EMA Length")
        self.atr_len = self.input.int(14, "ATR Length")
        self.atr_mult = self.input.float(1.5, "SL ATR Multiplier")

    def on_bar(self):
        ema200 = ta.ema(self.close, self.ema_len)
        atr = ta.atr(self.atr_len)
        self.plot(ema200, color=color.blue, linewidth=2)
        hh = S(ta.highest(self.high, 10))
        ll = S(ta.lowest(self.low, 10))
        buy_signal = self.low < ll[1] and self.close > ll[1] and self.close > ema200
        sell_signal = self.high > hh[1] and self.close < hh[1] and self.close < ema200
        st = self.strategy
        if buy_signal and st.position_size <= 0:
            st.entry("BUY", st.long)
        if sell_signal and st.position_size >= 0:
            st.entry("SELL", st.short)
        long_sl = st.position_avg_price - atr * self.atr_mult
        long_tp = st.position_avg_price + atr * self.atr_mult * 3
        st.exit("BUY EXIT", from_entry="BUY", stop=long_sl, limit=long_tp)
        short_sl = st.position_avg_price + atr * self.atr_mult
        short_tp = st.position_avg_price - atr * self.atr_mult * 3
        st.exit("SELL EXIT", from_entry="SELL", stop=short_sl, limit=short_tp)
        self.plotshape(buy_signal)
        self.plotshape(sell_signal)

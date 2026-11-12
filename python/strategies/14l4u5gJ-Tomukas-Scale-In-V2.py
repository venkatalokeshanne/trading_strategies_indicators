"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Tomukas Scale-In V2
Author       : Tomukasss
Source URL   : https://www.tradingview.com/script/14l4u5gJ-Tomukas-Scale-In-V2
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close: orders fill at the signal bar's close). In an EMA 100 / 200 up-trend, a bar that sweeps below the lowest low of the previous lookback bars but closes back above that low as an up candle is a long sweep (mirror for shorts in a down-trend).
While flat the first entry (quantity 1) is taken; while the position is open and the sweep repeats, the next scale-in entry is added by the number of open trades (quantities 2 .. 5, up to pyramiding 5). One exit order (take-profit ATR multiple above / below the average entry price) is re-issued each bar for the whole position.
Deviations from the original: none.
Not carried over: the BUY / SELL markers (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, ta


class TomukasScaleInV2(Script):
    TITLE = "Tomukas Scale-In V2"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=5, process_orders_on_close=True)
    SOURCE = {"id": "14l4u5gJ", "author": "Tomukasss", "licence": "not stated", "url": "https://www.tradingview.com/script/14l4u5gJ-Tomukas-Scale-In-V2"}

    def init(self):
        i = self.input
        self.lookback = i.int(20, "Sweep Lookback")
        self.q = [i.float(v, "Entry %d" % (k + 1)) for k, v in enumerate((10, 10, 20, 40, 80))]
        self.atr_len = i.int(14, "ATR Length")
        self.tp_atr = i.float(1.5, "TP ATR Multiplier")

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        ema100 = ta.ema(close, 100)
        ema200 = ta.ema(close, 200)
        bull_trend = ema100 > ema200
        bear_trend = ema100 < ema200
        prev_low = ta.lowest(self.low[1], self.lookback)
        prev_high = ta.highest(self.high[1], self.lookback)
        long_sweep = bull_trend and low < prev_low and close > prev_low and close > open_
        short_sweep = bear_trend and high > prev_high and close < prev_high and close < open_
        n = st.opentrades
        if long_sweep and st.position_size == 0:
            st.entry("L1", st.long, qty=self.q[0])
        if short_sweep and st.position_size == 0:
            st.entry("S1", st.short, qty=self.q[0])
        for k in range(1, 5):
            if st.position_size > 0 and long_sweep and n == k:
                st.entry("L%d" % (k + 1), st.long, qty=self.q[k])
        for k in range(1, 5):
            if st.position_size < 0 and short_sweep and n == k:
                st.entry("S%d" % (k + 1), st.short, qty=self.q[k])
        atr = ta.atr(self.atr_len)
        long_tp = st.position_avg_price + atr * self.tp_atr
        short_tp = st.position_avg_price - atr * self.tp_atr
        if st.position_size > 0:
            st.exit("TP LONG", limit=long_tp)
        if st.position_size < 0:
            st.exit("TP SHORT", limit=short_tp)

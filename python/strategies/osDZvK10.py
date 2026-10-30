"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : sebbiottino  Trailing Stop so good ger40 1m
Author       : sebbiottinofx
Source URL   : https://www.tradingview.com/script/osDZvK10
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The stops are manual ratchets: while in a position the stop is re-issued each
bar as the max (long) / min (short) of the lower / upper band since entry and cleared when flat, so a
position's first bar after a reversal has no stop. `src[lag]` inside the EMA argument goes through the
price series history.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, pmath, ta


class ZlemaTrailingStop(Script):
    TITLE = "sebbiottino  Trailing Stop so good ger40 1m "
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "osDZvK10", "author": "sebbiottinofx", "licence": "not stated",
              "url": "https://www.tradingview.com/script/osDZvK10"}

    def init(self):
        self.length = self.input.int(20, "Length")
        self.mult = self.input.float(0.2, "Band Multiplier")
        self.ema_length = self.input.int(15, "EMA Length")
        self.trend = 0
        self.long_stop = NA
        self.short_stop = NA

    def on_bar(self):
        src = self.close
        lag = pmath.floor((self.length - 1) / 2)
        zlema = ta.ema(src + (src - self.close[lag]), self.length)
        volatility = ta.highest(ta.atr(self.length), self.length * 3) * self.mult
        upper = zlema + volatility
        lower = zlema - volatility
        ema = ta.ema(self.close, self.ema_length)
        long_filter = self.close > ema
        short_filter = self.close < ema
        cross_up_upper = ta.crossover(self.close, upper)
        cross_dn_lower = ta.crossunder(self.close, lower)
        if cross_up_upper and long_filter:
            self.trend = 1
        if cross_dn_lower and short_filter:
            self.trend = -1
        cross_up_z = ta.crossover(self.close, zlema)
        cross_dn_z = ta.crossunder(self.close, zlema)
        long_entry = cross_up_z and self.trend == 1 and long_filter
        short_entry = cross_dn_z and self.trend == -1 and short_filter
        st = self.strategy
        if long_entry:
            st.entry("LONG", st.long)
        if short_entry:
            st.entry("SHORT", st.short)
        if st.position_size > 0:
            self.long_stop = lower if na(self.long_stop) else pmath.max(self.long_stop, lower)
            st.exit("LX", "LONG", stop=self.long_stop)
        if st.position_size < 0:
            self.short_stop = upper if na(self.short_stop) else pmath.min(self.short_stop, upper)
            st.exit("SX", "SHORT", stop=self.short_stop)
        if st.position_size == 0:
            self.long_stop = NA
            self.short_stop = NA
        self.plotshape(long_entry)
        self.plotshape(short_entry)
        self.plot(self.long_stop if st.position_size > 0 else NA, color=color.green, title="Long Stop")
        self.plot(self.short_stop if st.position_size < 0 else NA, color=color.red, title="Short Stop")

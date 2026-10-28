"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Moja Strategia Harami BB
Author       : cb85wj5jmt
Source URL   : https://www.tradingview.com/script/Cf6gXdy1-Moja-Strategia-Harami-BB
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation (same script as 1i9HDUUV under another id). A harami (the body of the current candle inside the previous one) after a candle
that touched the Bollinger band reverses the position. The two strategy.exit calls (profit 40 / loss 20 TICKS) are
unconditional and pending before each fill, so they already work on the fill bar.

Deviations from the original: none.
Not carried over: fill() between the bands and the signal labels (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color
from pinelib import pmath, ta


class MojaStrategiaHaramiBb(Script):
    TITLE = "Moja Strategia Harami BB"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000, default_qty_type="cash", default_qty_value=100)
    SOURCE = {"id": "Cf6gXdy1", "author": "cb85wj5jmt", "licence": "not stated",
              "url": "https://www.tradingview.com/script/Cf6gXdy1-Moja-Strategia-Harami-BB"}

    def init(self):
        self.bb_len = self.input.int(20, "BB Length")
        self.bb_mult = self.input.float(2.0, "BB Multiplier")

    def on_bar(self):
        ha_open, ha_high, ha_low, ha_close = self.open, self.high, self.low, self.close
        basis = ta.sma(ha_close, self.bb_len)
        dev = ta.stdev(ha_close, self.bb_len) * self.bb_mult
        upper_bb = S(basis + dev)
        lower_bb = S(basis - dev)
        self.plot(basis, "BB Basis", color=color.blue)
        self.plot(upper_bb, "Upper BB")
        self.plot(lower_bb, "Lower BB")
        prev_high = pmath.max(ha_open[1], ha_close[1])
        prev_low = pmath.min(ha_open[1], ha_close[1])
        curr_high = pmath.max(ha_open, ha_close)
        curr_low = pmath.min(ha_open, ha_close)
        first_touch_lower = ha_low[1] <= lower_bb[1]
        first_touch_upper = ha_high[1] >= upper_bb[1]
        body_inside = curr_high <= prev_high and curr_low >= prev_low
        bull_signal = first_touch_lower and (ha_close[1] < ha_open[1]) and body_inside
        bear_signal = first_touch_upper and (ha_close[1] > ha_open[1]) and body_inside
        st = self.strategy
        if bull_signal:
            st.entry("Long", st.long)
        if bear_signal:
            st.entry("Short", st.short)
        st.exit("TP/SL Long", from_entry="Long", profit=40, loss=20)
        st.exit("TP/SL Short", from_entry="Short", profit=40, loss=20)
        self.plotshape(bull_signal, title="Bull Harami")
        self.plotshape(bear_signal, title="Bear Harami")
        self.alertcondition(bull_signal, "Bull Harami Reversal", "Bullish Harami – First candle touched lower BB")
        self.alertcondition(bear_signal, "Bear Harami Reversal", "Bearish Harami – First candle touched upper BB")

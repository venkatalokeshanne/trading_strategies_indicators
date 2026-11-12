"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Micro-TL Final Balanced
Author       : version
Source URL   : https://www.tradingview.com/script/4NV68grw-Micro-Trendline-Momentum-Breakout-ATR-Optimized-Anant
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. ta.pivothigh / pivotlow(3, 1) feed var pivot pairs (value and bar index of the pivot, one bar
before the confirmation bar); the last two pivots define a resistance / support line extended to the current bar. A close
crossing over the resistance line above HMA(20) with RSI < 70 goes long (under the support line below the HMA with
RSI > 30 short), only when flat. The entry and its bracket (stop 1.5 ATR, limit 2 R) are issued together on the signal
bar, so the bracket also works on the fill bar.

Deviations from the original: none.
Not carried over: the HMA, trendline and stop plots (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, na, ta


class MicroTrendlineBreakout(Script):
    TITLE = "Micro-TL Final Balanced"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=15)
    SOURCE = {"id": "4NV68grw", "author": "version", "licence": "not stated",
              "url": "https://www.tradingview.com/script/4NV68grw-Micro-Trendline-Momentum-Breakout-ATR-Optimized-Anant"}

    def init(self):
        self.pivot_len = self.input.int(3, "Pivot Strength")
        self.rr_ratio = self.input.float(2.0, "Risk:Reward")
        self.atr_mult = self.input.float(1.5, "ATR Stop Multiplier")
        self.ph1 = self.ph2 = NA
        self.ph1_idx = self.ph2_idx = NA
        self.pl1 = self.pl2 = NA
        self.pl1_idx = self.pl2_idx = NA

    def on_bar(self):
        hma_filter = ta.hma(self.close, 20)
        rsi = ta.rsi(self.close, 14)
        ph = ta.pivothigh(self.pivot_len, 1)
        pl = ta.pivotlow(self.pivot_len, 1)
        if not na(ph):
            self.ph2, self.ph2_idx = self.ph1, self.ph1_idx
            self.ph1, self.ph1_idx = ph, self.bar_index - 1
        if not na(pl):
            self.pl2, self.pl2_idx = self.pl1, self.pl1_idx
            self.pl1, self.pl1_idx = pl, self.bar_index - 1
        res_price = self.ph1 + div(self.ph1 - self.ph2, self.ph1_idx - self.ph2_idx) * (self.bar_index - self.ph1_idx)
        sup_price = self.pl1 + div(self.pl1 - self.pl2, self.pl1_idx - self.pl2_idx) * (self.bar_index - self.pl1_idx)
        long_condition = ta.crossover(self.close, res_price) and self.close > hma_filter and rsi < 70
        short_condition = ta.crossunder(self.close, sup_price) and self.close < hma_filter and rsi > 30
        atr = ta.atr(14)
        st = self.strategy
        if long_condition and st.position_size == 0:
            sl = self.close - (atr * self.atr_mult)
            st.entry("Long", st.long)
            st.exit("ExL", "Long", stop=sl, limit=self.close + ((self.close - sl) * self.rr_ratio))
        if short_condition and st.position_size == 0:
            sl = self.close + (atr * self.atr_mult)
            st.entry("Short", st.short)
            st.exit("ExS", "Short", stop=sl, limit=self.close - ((sl - self.close) * self.rr_ratio))
        self.plot(hma_filter, color=color.purple, title="HMA Trend")
        self.plot(res_price, color=color.red, title="Resistance Line")
        self.plot(sup_price, color=color.green, title="Support Line")

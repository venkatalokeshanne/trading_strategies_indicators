"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : RSI Divergence + EMA Trend Filter
Author       : PinegenAI
Source URL   : https://www.tradingview.com/script/8oH4qCeH-RSI-Divergence-EMA-Trend-Filter
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Pivots (5 bars each side) are confirmed 5 bars later; ta.valuewhen(not na(pivot), x, n) reads x at
the confirmation bars (so `high` / `rsi` are those of the CONFIRMATION bar, as in the original). On a confirmation bar, a
higher high with a lower RSI than at the previous confirmation (bearish divergence) below EMA200 goes short; a lower low with
a higher RSI above EMA200 goes long, when flat. Entry and exit (stop = the pivot bar's low / high -/+ 1.5 ATR, target 3 ATR
from the close) are issued together on the signal bar, so the bracket also works on the fill bar.

Deviations from the original: none.
Not carried over: the EMA / RSI plots, shapes and hlines (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, na, ta


class RsiDivergenceEma(Script):
    TITLE = "RSI Divergence + EMA Trend Filter"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "8oH4qCeH", "author": "PinegenAI", "licence": "not stated",
              "url": "https://www.tradingview.com/script/8oH4qCeH-RSI-Divergence-EMA-Trend-Filter"}

    def init(self):
        self.rsi_len = self.input.int(14, "RSI Length", group="RSI")
        self.rsi_src = self.input.source(self.close, "RSI Source", group="RSI")
        self.lb_len = self.input.int(5, "Pivot Lookback", group="Divergence", minval=2)
        self.ema_len = self.input.int(200, "EMA Length", group="Trend Filter")
        self.atr_len = self.input.int(14, "ATR Length", group="Risk")
        self.sl_mult = self.input.float(1.5, "SL ATR Multiplier", group="Risk", step=0.1)
        self.tp_mult = self.input.float(3.0, "TP ATR Multiplier", group="Risk", step=0.1)

    def on_bar(self):
        rsi_val = ta.rsi(self.rsi_src, self.rsi_len)
        ema_val = ta.ema(self.close, self.ema_len)
        atr_val = ta.atr(self.atr_len)
        pivot_high = ta.pivothigh(self.high, self.lb_len, self.lb_len)
        pivot_low = ta.pivotlow(self.low, self.lb_len, self.lb_len)
        ph_ok = not na(pivot_high)
        pl_ok = not na(pivot_low)
        rsi_at_high = ta.valuewhen(ph_ok, rsi_val, 0)
        rsi_at_low = ta.valuewhen(pl_ok, rsi_val, 0)
        prev_rsi_high = ta.valuewhen(ph_ok, rsi_val, 1)
        prev_rsi_low = ta.valuewhen(pl_ok, rsi_val, 1)
        prev_pivot_high = ta.valuewhen(ph_ok, self.high, 1)
        prev_pivot_low = ta.valuewhen(pl_ok, self.low, 1)
        bear_div = ph_ok and self.high > prev_pivot_high and rsi_at_high < prev_rsi_high
        bull_div = pl_ok and self.low < prev_pivot_low and rsi_at_low > prev_rsi_low
        above_ema = self.close > ema_val
        below_ema = self.close < ema_val
        st = self.strategy
        long_cond = bull_div and above_ema and self.barstate.isconfirmed and st.position_size == 0
        short_cond = bear_div and below_ema and self.barstate.isconfirmed and st.position_size == 0
        if long_cond:
            st.entry("Long", st.long)
            st.exit("Long Exit", "Long", stop=self.low[self.lb_len] - atr_val * self.sl_mult, limit=self.close + atr_val * self.tp_mult)
        if short_cond:
            st.entry("Short", st.short)
            st.exit("Short Exit", "Short", stop=self.high[self.lb_len] + atr_val * self.sl_mult, limit=self.close - atr_val * self.tp_mult)
        self.plot(ema_val, "EMA Trend Filter", color=color.blue)

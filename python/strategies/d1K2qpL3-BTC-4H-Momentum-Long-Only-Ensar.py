"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : BTC 4H Momentum — Long Only [Ensar]
Author       : ensararikan
Source URL   : https://www.tradingview.com/script/d1K2qpL3-BTC-4H-Momentum-Long-Only-Ensar
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Long only: close over a rising EMA200 (compared with 10 bars ago), 20-bar rate of
change above the threshold and ADX above 20, only when flat. The stop is the CURRENT bar's 7-bar low and the
target is 3R from the signal close, placed with the entry (works from the fill bar).

Deviations from the original: none.
Not carried over: the entry label (label.new with the price text, never read back).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color, div, ta


class BtcMomentumLongOnly(Script):
    TITLE = "BTC 4H Momentum — Long Only [Ensar]"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=40,
                    commission_type="percent", commission_value=0.1, slippage=2)
    SOURCE = {"id": "d1K2qpL3", "author": "ensararikan", "licence": "not stated",
              "url": "https://www.tradingview.com/script/d1K2qpL3-BTC-4H-Momentum-Long-Only-Ensar"}

    def init(self):
        self.roc_len = self.input.int(20, "ROC Length", minval=5)
        self.roc_thr = self.input.float(1.0, "ROC Threshold (%)", minval=0.1)
        self.ema_len = self.input.int(200, "EMA Length (Trend)", minval=50)
        self.swing_lb = self.input.int(7, "Swing Lookback", minval=3)
        self.rr_target = self.input.float(3.0, "R:R Target", minval=1.0)
        self.adx_len = self.input.int(14, "ADX Length", minval=5)
        self.adx_thr = self.input.int(20, "ADX Threshold", minval=10)
        self.ema_dir_bars = self.input.int(10, "EMA Direction (bars)", minval=3)

    def on_bar(self):
        ema200 = S(ta.ema(self.close, self.ema_len))
        roc = div(self.close - self.close[self.roc_len], self.close[self.roc_len]) * 100
        swing_low = ta.lowest(self.low, self.swing_lb)
        diplus, diminus, adx = ta.dmi(self.adx_len, self.adx_len)
        self.plot(ema200, color=color.orange, linewidth=2, title="200 EMA")
        ema_rising = ema200 > ema200[self.ema_dir_bars]
        long_cond = self.close > ema200 and ema_rising and roc > self.roc_thr and adx > self.adx_thr
        st = self.strategy
        no_pos = st.position_size == 0
        if long_cond and no_pos:
            sl = swing_low
            tp = self.close + (self.close - sl) * self.rr_target
            st.entry("Long", st.long)
            st.exit("Long TP/SL", "Long", stop=sl, limit=tp, comment_loss="SL", comment_profit="TP")
        self.plotshape(long_cond and no_pos, title="Long Signal")
        self.alertcondition(long_cond and no_pos, "Long Signal", "BTC 4H Momentum — Long Signal on {{ticker}}")

"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : XAU Clear EMA ATR Strategy TP SL Voice V6
Author       : ionplesu88
Source URL   : https://www.tradingview.com/script/zudiHFjK-XAU-Clear-EMA-ATR-Strategy-TP-SL-Voice-V6
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close: orders fill at the signal bar's close). A close back above the fast EMA (from at or below it on the previous bar) with the fast EMA over the slow one is a buy; the mirror image is a sell. A signal opposite to the open position closes it and enters the new side;
the entry price is the signal close rounded to the tick, the stop is ATR x multiplier away and five targets sit at the given multiples of that risk. From the signal on, five exit orders of 20 % each (limit at their target, all with the stop) are re-issued every bar for the current direction.
A signal in the direction of an open position cannot add to it (no pyramiding) but moves the levels of its exit orders. 
Deviations from the original: none.
Not carried over: the entry / stop / target labels and the voice alerts (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, pmath, ta


class XauClearEmaAtr(Script):
    TITLE = "XAU Clear EMA ATR Strategy TP SL Voice V6"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(process_orders_on_close=True)
    SOURCE = {"id": "zudiHFjK", "author": "ionplesu88", "licence": "not stated",
              "url": "https://www.tradingview.com/script/zudiHFjK-XAU-Clear-EMA-ATR-Strategy-TP-SL-Voice-V6"}

    def init(self):
        i = self.input
        self.fast_len = i.int(21, "EMA Fast")
        self.slow_len = i.int(50, "EMA Slow")
        self.atr_len = i.int(14, "ATR Length")
        self.sl_atr = i.float(1.5, "SL ATR Multiplier")
        self.tp1_r = i.float(0.7, "TP1 STRONG")
        self.tp2_r = i.float(1.2, "TP2 STRONG")
        self.tp3_r = i.float(1.8, "TP3 GOOD")
        self.tp4_r = i.float(2.5, "TP4 AGGRESSIVE")
        self.tp5_r = i.float(3.5, "TP5 AGGRESSIVE")
        self.entry = NA
        self.sl = NA
        self.tps = [NA] * 5
        self.dir = 0

    def round_price(self, x):
        return pmath.round(div(x, self.syminfo.mintick)) * self.syminfo.mintick

    def on_bar(self):
        st = self.strategy
        close = self.close
        ema_fast = ta.ema(close, self.fast_len)
        ema_slow = ta.ema(close, self.slow_len)
        atr_value = ta.atr(self.atr_len)
        ema_fast_1 = self.H("ema_fast")[1]
        self.H("ema_fast").set(ema_fast)
        close_1 = self.close[1]
        buy_signal = ema_fast > ema_slow and close > ema_fast and close_1 <= ema_fast_1
        sell_signal = ema_fast < ema_slow and close < ema_fast and close_1 >= ema_fast_1
        mults = (self.tp1_r, self.tp2_r, self.tp3_r, self.tp4_r, self.tp5_r)
        if buy_signal:
            self.entry = self.round_price(close)
            self.sl = self.round_price(self.entry - atr_value * self.sl_atr)
            risk = self.entry - self.sl
            self.tps = [self.round_price(self.entry + risk * m) for m in mults]
            self.dir = 1
            st.close("SELL")
            st.entry("BUY", st.long)
        if sell_signal:
            self.entry = self.round_price(close)
            self.sl = self.round_price(self.entry + atr_value * self.sl_atr)
            risk = self.sl - self.entry
            self.tps = [self.round_price(self.entry - risk * m) for m in mults]
            self.dir = -1
            st.close("BUY")
            st.entry("SELL", st.short)
        if self.dir == 1:
            for k in range(5):
                st.exit("BUY TP" + str(k + 1), "BUY", limit=self.tps[k], stop=self.sl, qty_percent=20)
        if self.dir == -1:
            for k in range(5):
                st.exit("SELL TP" + str(k + 1), "SELL", limit=self.tps[k], stop=self.sl, qty_percent=20)

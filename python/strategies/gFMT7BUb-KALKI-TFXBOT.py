"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : KALKI TFXBOT
Author       : KalkiTrader007
Source URL   : https://www.tradingview.com/script/gFMT7BUb-KALKI-TFXBOT
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). The latest confirmed swing low / high (10 bars left, 3 right) are the liquidity floor / ceiling; a bar whose wick
sweeps below the floor and closes back above it as an up bar above the EMA200 goes long (the mirror goes short), closing an opposite position first. The stop
(beyond the sweeping wick plus the buffer) and the R:R target are fixed at the signal bar.

Deviations from the original: none.
Not carried over: entry / stop / target boxes, the HUD table and the swing circles (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, ta


class KalkiTFXBot(Script):
    TITLE = "KALKI TFXBOT"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100, default_qty_type="fixed", default_qty_value=1, margin_long=0, margin_short=0, process_orders_on_close=True)
    SOURCE = {"id": "gFMT7BUb", "author": "KalkiTrader007", "licence": "not stated",
              "url": "https://www.tradingview.com/script/gFMT7BUb-KALKI-TFXBOT"}

    def init(self):
        g = "🛡️ CARTEL RISK MANAGEMENT"
        self.rr = self.input.float(3.0, "Risk to Reward Ratio (e.g. 3 = 1:3 RR)", step=0.5, group=g)
        self.sl_buffer = self.input.float(0.5, "Stop Loss Buffer (Pips)", step=0.1, group=g)
        g = "⚡ SMC FILTERS"
        self.ema_trend = self.input.int(200, "EMA Trend Guard", group=g)
        self.pivot_l = self.input.int(10, "Swing Left Lookback", group=g)
        self.pivot_r = self.input.int(3, "Swing Right Lookback", group=g)
        self.current_sup = NA
        self.current_res = NA

    def on_bar(self):
        ema200 = ta.ema(self.close, self.ema_trend)
        pl = ta.pivotlow(self.low, self.pivot_l, self.pivot_r)
        ph = ta.pivothigh(self.high, self.pivot_l, self.pivot_r)
        if not na(pl):
            self.current_sup = pl
        if not na(ph):
            self.current_res = ph
        sweep_buy = self.low < self.current_sup and self.close > self.current_sup and self.close > self.open and self.close > ema200
        sweep_sell = self.high > self.current_res and self.close < self.current_res and self.close < self.open and self.close < ema200
        st = self.strategy
        if sweep_buy and st.position_size <= 0:
            if st.position_size < 0:
                st.close("Short", comment="REVERSAL")
            entry_price = float(self.close)
            sl_price = self.low - (self.sl_buffer / 10)
            risk_amt = entry_price - sl_price
            tp_price = entry_price + risk_amt * self.rr
            st.entry("Long", st.long, comment="SWEEP BUY")
            st.exit("Exit Long", "Long", stop=sl_price, limit=tp_price)
        if sweep_sell and st.position_size >= 0:
            if st.position_size > 0:
                st.close("Long", comment="REVERSAL")
            entry_price = float(self.close)
            sl_price = self.high + (self.sl_buffer / 10)
            risk_amt = sl_price - entry_price
            tp_price = entry_price - risk_amt * self.rr
            st.entry("Short", st.short, comment="SWEEP SELL")
            st.exit("Exit Short", "Short", stop=sl_price, limit=tp_price)
        self.plot(self.current_sup, "Liquidity Floor", color=color.blue)
        self.plot(self.current_res, "Liquidity Ceiling", color=color.red)

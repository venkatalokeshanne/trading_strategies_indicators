"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : [3Commas] Gold DCA Long — XAUT/USDT
Author       : 3Commas
Source URL   : https://www.tradingview.com/script/j36wYVnI-3Commas-Gold-Vault-Long
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation of a 3Commas DCA-bot template (market orders at the next open, pending limit orders for the safety orders). While no deal is open (inside the date window) a base order of a fixed quote amount is bought;
the script then tracks the deal itself (base price, total volume, total quantity, safety-order count): each bar whose low reaches the next safety-order trigger (a geometric ladder of deviations below the base price) places a
LIMIT entry "SOn" at that trigger price - several can be placed on one bar - and books it at once into the volume / quantity totals; the deal is closed with strategy.close_all when the high reaches the take-profit percentage above the booked average price.
Quirks kept: the average price / take-profit level are computed at the top of the bar (before that bar's orders update the totals); the totals are booked when the order is PLACED, not when it fills; close_all does not cancel limit orders still pending, and the pyramiding limit (1 base + 3 safety orders) silently drops a fill beyond it.
Deviations from the original: none.
Not carried over: the webhook inputs, plots / labels / backgrounds, stats card and watermark tables (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath

START_TS = 1741132800000      # timestamp("2025-03-05 00:00 +0000")
END_TS = 1778803140000        # timestamp("2026-05-14 23:59 +0000")


class GoldDcaLong(Script):
    TITLE = "[3Commas] Gold DCA Long — XAUT/USDT"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=500, default_qty_type="cash", default_qty_value=12, pyramiding=4, commission_type="percent",
                    commission_value=0.1, slippage=2)
    SOURCE = {"id": "j36wYVnI", "author": "3Commas", "licence": "not stated", "url": "https://www.tradingview.com/script/j36wYVnI-3Commas-Gold-Vault-Long"}

    def init(self):
        i = self.input
        g = "DCA / Safety Orders"
        self.bo_vol = i.float(12.0, "Base Order Volume (USDT)", group=g)
        self.so_vol = i.float(9.0, "Safety Order Volume (USDT)", group=g)
        self.max_so = i.int(4, "Max Safety Orders", minval=0, maxval=15, group=g)
        self.so_step = i.float(2.0, "Price Step % (1st SO from base)", step=0.05, group=g)
        self.step_coef = i.float(1.0, "Deviation Step Multiplier", step=0.01, group=g)
        self.vol_coef = i.float(1.05, "Order Size Multiplier", step=0.01, group=g)
        self.tp_pct = i.float(1.5, "Take Profit % (from avg entry)", minval=0.01, step=0.05, group="Take Profit") / 100.0
        g = "Backtest Period"
        self.use_dates = i.bool(True, "Limit by Date Range", group=g)
        self.start_ts = i.time(START_TS, "Start", group=g)
        self.end_ts = i.time(END_TS, "End", group=g)
        self.in_deal = False
        self.base_price = NA
        self.total_volume = 0.0
        self.total_qty = 0.0
        self.so_count = 0

    def so_trigger_price(self, n):
        dev = 0.0
        s = self.so_step
        for _ in range(1, n + 1):
            dev = dev + s
            s = s * self.step_coef
        return self.base_price * (1.0 - dev / 100.0)

    def so_volume(self, n):
        return self.so_vol * pmath.pow(self.vol_coef, n - 1)

    def on_bar(self):
        st = self.strategy
        close = self.close
        in_window = (not self.use_dates) or (self.time >= self.start_ts and self.time <= self.end_ts)
        avg_price = div(self.total_volume, self.total_qty) if self.total_qty > 0 else NA
        tp_price = NA if na(avg_price) else avg_price * (1.0 + self.tp_pct)
        if not self.in_deal and in_window:
            qty = div(self.bo_vol, close)
            st.entry("BO", st.long, qty=qty)
            self.in_deal = True
            self.base_price = float(close)
            self.total_volume = self.bo_vol
            self.total_qty = qty
            self.so_count = 0
        if self.in_deal:
            while self.so_count < self.max_so:
                next_so = self.so_count + 1
                trig = self.so_trigger_price(next_so)
                if self.low <= trig:
                    v = self.so_volume(next_so)
                    q = div(v, trig)
                    st.entry("SO" + str(next_so), st.long, qty=q, limit=trig)
                    self.total_volume = self.total_volume + v
                    self.total_qty = self.total_qty + q
                    self.so_count = next_so
                else:
                    break
        price_ok = (not na(tp_price)) and self.high >= tp_price
        if self.in_deal and price_ok:
            st.close_all(comment="TP")
            self.in_deal = False
            self.base_price = NA
            self.total_volume = 0.0
            self.total_qty = 0.0
            self.so_count = 0

"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : [3Commas] INTCUSDT Long DCA — RSI Exit
Author       : 3Commas
Source URL   : https://www.tradingview.com/script/GhH6mW5c-3Commas-Silicon-Vault-Long-INTC-DCA-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation of a 3Commas DCA-bot template (market orders at the next open, pending limit orders for the safety orders). While no deal is open (inside the date window) a base order of a fixed quote amount is bought;
the script then tracks the deal itself (base price, total volume, total quantity, safety-order count): each bar whose low reaches the next safety-order trigger (a geometric ladder of deviations below the base price) places a
LIMIT entry "SOn" at that trigger price - several can be placed on one bar - and books it at once into the volume / quantity totals; the deal is closed with strategy.close_all when the CLOSE is at least the take-profit percentage above the booked average price
and (optionally) the previous bar's RSI (request.security on the RSI timeframe, expression [1], lookahead on) has crossed above the threshold.
Quirks kept: the average price / take-profit level are computed at the top of the bar (before that bar's orders update the totals); the totals are booked when the order is PLACED, not when it fills; close_all does not cancel limit orders still pending, and the pyramiding limit (1 base + 8 safety orders) silently drops a fill beyond it.
Deviations from the original: none.
Not carried over: the webhook inputs, plots / labels / backgrounds, stats card and watermark tables (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta



def make_prev_rsi(length):
    """ta.rsi(close, length)[1] on the requested bars."""
    state = dict(prev=NA)

    def prev_rsi(v):
        r = ta.rsi(v.close, length)
        out = state["prev"]
        state["prev"] = r
        return out
    return prev_rsi


START_TS = 1735689600000      # timestamp("2025-01-01 00:00 +0000")
END_TS = 1778803140000        # timestamp("2026-05-14 23:59 +0000")


class IntcDcaLongRsiExit(Script):
    TITLE = "[3Commas] INTCUSDT Long DCA — RSI Exit"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=500, default_qty_type="cash", default_qty_value=11.25, pyramiding=9, commission_type="percent",
                    commission_value=0.06, slippage=2, margin_long=50.0)
    SOURCE = {"id": "GhH6mW5c", "author": "3Commas", "licence": "not stated", "url": "https://www.tradingview.com/script/GhH6mW5c-3Commas-Silicon-Vault-Long-INTC-DCA-Strategy"}

    def init(self):
        i = self.input
        g = "DCA / Safety Orders"
        self.bo_vol = i.float(11.25, "Base Order Volume (USDT)", group=g)
        self.so_vol = i.float(7.5, "Safety Order Volume (USDT)", group=g)
        self.max_so = i.int(8, "Max Safety Orders", minval=0, maxval=20, group=g)
        self.so_step = i.float(0.5, "Price Step % (1st SO from base)", step=0.05, group=g)
        self.step_coef = i.float(1.22, "Martingale Step Coefficient", step=0.01, group=g)
        self.vol_coef = i.float(1.0, "Martingale Volume Coefficient", step=0.01, group=g)
        g = "Take Profit — RSI Gate"
        self.use_exit_rsi = i.bool(True, "Require RSI cross-above for close", group=g)
        self.rsi_len = i.int(14, "RSI Length", minval=2, group=g)
        self.rsi_thr = i.float(70, "RSI Threshold", group=g)
        self.rsi_tf = i.timeframe("15", "RSI Timeframe", group=g)
        self.min_profit = i.float(0.6, "Min Profit % (from avg entry)", minval=0.01, step=0.05, group=g) / 100.0
        g = "Backtest Period"
        self.use_dates = i.bool(True, "Limit by Date Range", group=g)
        self.start_ts = i.time(START_TS, "Start", group=g)
        self.end_ts = i.time(END_TS, "End", group=g)
        self.prev_rsi = make_prev_rsi(self.rsi_len)
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
        rsi_val = self.security(None, self.rsi_tf, self.prev_rsi, lookahead=True)
        rsi_sig = ta.crossover(rsi_val, self.rsi_thr)
        in_window = (not self.use_dates) or (self.time >= self.start_ts and self.time <= self.end_ts)
        avg_price = div(self.total_volume, self.total_qty) if self.total_qty > 0 else NA
        tp_price = NA if na(avg_price) else avg_price * (1.0 + self.min_profit)
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
        can_close_by_signal = (not self.use_exit_rsi) or rsi_sig
        price_ok = (not na(tp_price)) and close >= tp_price
        if self.in_deal and can_close_by_signal and price_ok:
            st.close_all(comment="TP+RSI" if self.use_exit_rsi else "TP")
            self.in_deal = False
            self.base_price = NA
            self.total_volume = 0.0
            self.total_qty = 0.0
            self.so_count = 0

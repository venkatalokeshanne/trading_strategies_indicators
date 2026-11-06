"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Multi Long Bot — Single-Pair Replica ([3Commas] Triple RSI DCA Long)
Author       : 3Commas
Source URL   : https://www.tradingview.com/script/u4g3IrXS-3Commas-Triple-RSI-DCA-Long-Risk-Adjusted-Averaging-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open; chart at or below the shortest RSI timeframe). A base order buys when the previous completed bar's 15-minute RSI crosses above its threshold (request.security with lookahead on and the expression offset by one bar, so no future data) while no deal is open;
safety orders (martingale volume and step) buy when the low reaches the next deviation level below the base price and one of two other-timeframe RSIs (30m, 5m, same previous-bar trick) has just crossed above its threshold; the deal closes at the next open once the high reaches the take-profit percentage above the
deal's running average price (computed from the intended fill prices, as in the original).
Deviations from the original: none.
Not carried over: plots, signal shapes, the background tint, the alert messages (display only).
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


FROM_TS = 1704067200000     # timestamp("2024-01-01 00:00 +0000")
TO_TS = 1893456000000       # timestamp("2030-01-01 00:00 +0000")


class MultiLongBotTripleRsi(Script):
    TITLE = "Multi Long Bot — Single-Pair Replica"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=200, default_qty_type="cash", default_qty_value=20.075, commission_type="percent", commission_value=0.1, slippage=5, pyramiding=4)
    SOURCE = {"id": "u4g3IrXS", "author": "3Commas", "licence": "not stated",
              "url": "https://www.tradingview.com/script/u4g3IrXS-3Commas-Triple-RSI-DCA-Long-Risk-Adjusted-Averaging-Strategy"}

    def init(self):
        i = self.input
        g = "USD-Multi — Order Sizing"
        self.bo_vol = i.float(20.075, "Base Order Volume (USD)", minval=0.5, step=0.001, group=g)
        self.so_vol = i.float(15.075, "Safety Order Volume (1st, USD)", minval=0.5, step=0.001, group=g)
        self.max_so = i.int(3, "Max Safety Orders", minval=0, maxval=10, group=g)
        self.vol_scale = i.float(1.9, "Volume Scale (martingale)", minval=1.0, step=0.01, group=g)
        g = "USD-Multi — Price Deviation"
        self.step_pct = i.float(1.0, "Price Step % (1st SO)", minval=0.01, step=0.05, group=g) * 0.01
        self.step_scale = i.float(1.65, "Step Scale (martingale)", minval=1.0, step=0.01, group=g)
        self.tp_pct = i.float(1.9, "Take Profit % (from AVG)", minval=0.01, step=0.05, group="USD-Multi — Take Profit") * 0.01
        g = "USD-Multi — Entry Signal (deal start)"
        self.use_entry_rsi = i.bool(True, "Require RSI cross-above for BO entry", group=g)
        self.entry_len = i.int(14, "Entry RSI Length", minval=2, group=g)
        self.entry_thr = i.float(30, "Entry RSI Threshold", group=g)
        self.entry_tf = i.timeframe("15", "Entry RSI Timeframe", group=g)
        g = "USD-Multi — SO Signals"
        self.use_so_signal = i.bool(True, "Require RSI cross-above for SO entry (OR of two TFs)", group=g)
        self.so1_len = i.int(14, "SO Sig 1 — RSI Length", minval=2, group=g)
        self.so1_thr = i.float(30, "SO Sig 1 — RSI Threshold", group=g)
        self.so1_tf = i.timeframe("30", "SO Sig 1 — RSI Timeframe", group=g)
        self.so2_len = i.int(7, "SO Sig 2 — RSI Length", minval=2, group=g)
        self.so2_thr = i.float(30, "SO Sig 2 — RSI Threshold", group=g)
        self.so2_tf = i.timeframe("5", "SO Sig 2 — RSI Timeframe", group=g)
        g = "USD-Multi — Backtest Window"
        self.use_date_filter = i.bool(False, "Limit by date window?", group=g)
        self.from_ts = i.time(FROM_TS, "From", group=g)
        self.to_ts = i.time(TO_TS, "To", group=g)
        self.prev_entry = make_prev_rsi(self.entry_len)
        self.prev_so1 = make_prev_rsi(self.so1_len)
        self.prev_so2 = make_prev_rsi(self.so2_len)
        self.base_px = NA
        self.avg_px = NA
        self.cost_sum = 0.0
        self.qty_sum = 0.0
        self.so_filled = 0

    def cum_dev(self, k):
        s = 0.0
        if k > 0:
            for j in range(k):
                s += pmath.pow(self.step_scale, j)
        return s * self.step_pct

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        in_window = ((self.time >= self.from_ts and self.time <= self.to_ts) if self.use_date_filter else True)
        entry_rsi = self.security(None, self.entry_tf, self.prev_entry, lookahead=True)
        entry_signal = ta.crossover(entry_rsi, self.entry_thr) if self.use_entry_rsi else True
        so1_rsi = self.security(None, self.so1_tf, self.prev_so1, lookahead=True)
        so2_rsi = self.security(None, self.so2_tf, self.prev_so2, lookahead=True)
        so1_cross = ta.crossover(so1_rsi, self.so1_thr)
        so2_cross = ta.crossover(so2_rsi, self.so2_thr)
        so_sig = (so1_cross or so2_cross) if self.use_so_signal else True
        next_idx = self.so_filled + 1
        next_dev = self.cum_dev(next_idx) if (next_idx > 0 and next_idx <= self.max_so) else NA
        next_px = self.base_px * (1.0 - next_dev) if (not na(self.base_px) and not na(next_dev)) else NA
        next_usd = self.so_vol * pmath.pow(self.vol_scale, pmath.max(self.so_filled, 0))
        pos = st.position_size
        if in_window and pos == 0 and na(self.base_px) and entry_signal:
            fill_px = float(close)
            qty = div(self.bo_vol, fill_px)
            st.entry("BO", st.long, qty=qty)
            self.base_px = fill_px
            self.avg_px = fill_px
            self.cost_sum = self.bo_vol
            self.qty_sum = qty
            self.so_filled = 0
        if in_window and pos > 0 and self.so_filled < self.max_so and not na(next_px):
            if low <= next_px and so_sig:
                exec_px = pmath.min(open_, next_px)
                qty = div(next_usd, exec_px)
                st.entry("SO" + str(next_idx), st.long, qty=qty)
                self.cost_sum = self.cost_sum + next_usd
                self.qty_sum = self.qty_sum + qty
                self.avg_px = div(self.cost_sum, self.qty_sum)
                self.so_filled = self.so_filled + 1
        tp_px = self.avg_px * (1.0 + self.tp_pct) if not na(self.avg_px) else NA
        if pos > 0 and not na(tp_px) and high >= tp_px and in_window:
            st.close_all(comment="TP")
            self.base_px = NA
            self.avg_px = NA
            self.cost_sum = 0.0
            self.qty_sum = 0.0
            self.so_filled = 0

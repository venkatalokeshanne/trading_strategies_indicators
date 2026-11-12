"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Dual RSI DCA — Long Strategy
Author       : 3Commas
Source URL   : https://www.tradingview.com/script/qgofvS9I-Dual-RSI-DCA-Long-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation of a 3Commas DCA-bot template (orders processed at the bar close, process_orders_on_close). When the higher-timeframe RSI (request.security, lookahead off) crosses up through the level and no trade is open (inside the backtest window),
a base order of a fixed quote amount buys at the close (or as a limit order at the close when "Use LIMIT for Base" is on); up to N averaging orders are added as the close falls through a geometric ladder of deviations from the base entry price (each step a multiple of the previous one)
with geometrically growing sizes; everything is closed at the bar close when a second RSI crosses down through its level while the close is at least the minimum-profit percentage above the average entry price.
Deviations from the original: none.
Not carried over: the webhook alert text, AO ladder lines / labels, status table, watermark table and plots (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, nz, pmath, ta

FROM_DATE = 1704067200000     # timestamp("01 Jan 2024 00:00 +0000")
TO_DATE = 1893456000000       # timestamp("01 Jan 2030 00:00 +0000")


class DualRsiDcaLongqgofvS9I(Script):
    TITLE = "Dual RSI DCA — Long Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="cash", default_qty_value=90, pyramiding=6, commission_type="percent",
                    commission_value=0.08, slippage=3, process_orders_on_close=True)
    SOURCE = {"id": "qgofvS9I", "author": "3Commas", "licence": "not stated", "url": "https://www.tradingview.com/script/qgofvS9I-Dual-RSI-DCA-Long-Strategy"}

    def init(self):
        i = self.input
        g = "Base Order"
        self.base_order_size = i.float(90.0, "Base Order Size (USDT)", minval=1, group=g)
        self.use_limit_base = i.bool(False, "Use LIMIT for Base (else Market)", group=g)
        g = "Averaging Orders"
        self.ao_count = i.int(5, "Averaging Orders per Trade", minval=0, maxval=10, group=g)
        self.ao_size = i.float(110.0, "First AO Size (USDT)", minval=1, group=g)
        self.ao_step = i.float(1.3, "Deviation to First AO (%)", minval=0.1, step=0.1, group=g)
        self.ao_step_mult = i.float(1.3, "Deviation Step Multiplier", minval=1.0, step=0.1, group=g)
        self.ao_size_mult = i.float(1.25, "Order Size Multiplier", minval=1.0, step=0.05, group=g)
        g = "Entry RSI Filter"
        self.entry_tf = i.timeframe("3", "RSI Timeframe", group=g)
        self.entry_rsi_len = i.int(14, "RSI Length", minval=2, group=g)
        self.entry_rsi_level = i.float(31.0, "RSI Crossing Up Level", minval=1, maxval=100, group=g)
        g = "Exit RSI"
        self.exit_tf = i.timeframe("3", "Exit RSI Timeframe", group=g)
        self.exit_rsi_len = i.int(14, "Exit RSI Length", minval=2, group=g)
        self.exit_rsi_level = i.float(69.0, "RSI Crossing Down Level", minval=1, maxval=100, group=g)
        self.min_profit_pct = i.float(2.4, "Minimum Profit (%)", minval=0.1, step=0.1, group=g)
        g = "Backtest Window"
        self.use_date_filter = i.bool(False, "Limit Backtest Period", group=g)
        self.from_date = i.time(FROM_DATE, "From", group=g)
        self.to_date = i.time(TO_DATE, "To", group=g)
        self.base_entry = NA
        self.ao_filled = 0
        self.prev_pos = NA

    def cum_dev(self, k):
        dev = 0.0
        step = self.ao_step
        for j in range(1, k + 1):
            if j == 1:
                dev = step
            else:
                step = step * self.ao_step_mult
                dev = dev + step
        return dev

    def ao_size_at(self, k):
        return self.ao_size * pmath.pow(self.ao_size_mult, k - 1)

    def on_bar(self):
        st = self.strategy
        close = self.close
        in_window = (not self.use_date_filter) or (self.time >= self.from_date and self.time <= self.to_date)
        entry_rsi = self.security(None, self.entry_tf, lambda v: ta.rsi(v.close, self.entry_rsi_len), lookahead=False)
        exit_rsi = self.security(None, self.exit_tf, lambda v: ta.rsi(v.close, self.exit_rsi_len), lookahead=False)
        er_h, xr_h = self.H("entry_rsi"), self.H("exit_rsi")
        entry_rsi_1, exit_rsi_1 = er_h[1], xr_h[1]
        er_h.set(entry_rsi)
        xr_h.set(exit_rsi)
        entry_cross_up = bool(entry_rsi_1 < self.entry_rsi_level and entry_rsi >= self.entry_rsi_level)
        exit_cross_down = bool(exit_rsi_1 > self.exit_rsi_level and exit_rsi <= self.exit_rsi_level)
        entry_cond = entry_cross_up
        in_position = st.position_size != 0
        just_entered = nz(self.prev_pos) == 0 and in_position
        position_just_flat = nz(self.prev_pos) != 0 and not in_position
        if just_entered and na(self.base_entry):
            self.base_entry = st.position_avg_price
            self.ao_filled = 0
        if position_just_flat or not in_position:
            self.base_entry = NA
            self.ao_filled = 0
        open_base = in_window and (not in_position) and st.opentrades == 0 and entry_cond
        if open_base:
            base_qty = div(self.base_order_size, close)
            if self.use_limit_base:
                st.entry("Long_Base", st.long, qty=base_qty, limit=close, comment="Long_Base")
            else:
                st.entry("Long_Base", st.long, qty=base_qty, comment="Long_Base")
        if in_position and in_window and self.ao_filled < self.ao_count and not na(self.base_entry):
            next_idx = self.ao_filled + 1
            threshold = self.cum_dev(next_idx)
            trigger_px = self.base_entry * (1.0 - threshold / 100.0)
            if close <= trigger_px:
                ao_qty_usdt = self.ao_size_at(next_idx)
                st.entry("Long_AO_" + str(next_idx), st.long, qty=div(ao_qty_usdt, close), comment="Long_AO_" + str(next_idx))
                self.ao_filled = next_idx
        if in_position:
            avg_px = st.position_avg_price
            min_tp_price = avg_px * (1.0 + self.min_profit_pct / 100.0)
            profit_armed = close >= min_tp_price
            if profit_armed and exit_cross_down:
                st.close_all(comment="RSI_TP")
        self.prev_pos = st.position_size

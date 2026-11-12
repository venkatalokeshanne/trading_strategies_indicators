"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : BB-RSI Overbought DCA — Short Strategy
Author       : 3Commas
Source URL   : https://www.tradingview.com/script/PnnQc7fs-BB-RSI-Overbought-DCA-Short-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation of a 3Commas DCA-bot template (orders processed at the bar close, process_orders_on_close). When the higher-timeframe RSI (request.security, lookahead off) has both its Bollinger %B and its RSI cross up through their levels and no trade is open (inside the backtest window),
a base order of a fixed quote amount sells short at the close (or as a limit order at the close when "Use LIMIT for Base" is on); up to N averaging orders are added as the close rises through a geometric ladder of deviations from the base entry price (each step a multiple of the previous one)
with geometrically growing sizes; everything is closed at the bar close once the close reaches the take-profit percentage below the average entry price.
Deviations from the original: none.
Not carried over: the webhook alert text, AO ladder lines / labels, status table, watermark table and plots (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, nz, pmath, ta

FROM_DATE = 1741564800000     # timestamp("10 Mar 2025 00:00 +0000")
TO_DATE = 1775087940000       # timestamp("01 Apr 2026 23:59 +0000")


class BbRsiOverboughtShort(Script):
    TITLE = "BB-RSI Overbought DCA — Short Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="cash", default_qty_value=80, pyramiding=10, commission_type="percent",
                    commission_value=0.4, slippage=3, process_orders_on_close=True)
    SOURCE = {"id": "PnnQc7fs", "author": "3Commas", "licence": "not stated", "url": "https://www.tradingview.com/script/PnnQc7fs-BB-RSI-Overbought-DCA-Short-Strategy"}

    def init(self):
        i = self.input
        g = "Base Order"
        self.base_order_size = i.float(80.0, "Base Order Size (USDC)", minval=1, group=g)
        self.use_limit_base = i.bool(False, "Use LIMIT for Base (else Market)", group=g)
        g = "Averaging Orders"
        self.ao_count = i.int(9, "Averaging Orders per Trade", minval=0, maxval=15, group=g)
        self.ao_size = i.float(80.0, "First AO Size (USDC)", minval=1, group=g)
        self.ao_step = i.float(0.72, "Deviation to First AO (%)", minval=0.1, step=0.01, group=g)
        self.ao_step_mult = i.float(1.55, "Deviation Step Multiplier", minval=1.0, step=0.05, group=g)
        self.ao_size_mult = i.float(1.03, "Order Size Multiplier", minval=1.0, step=0.01, group=g)
        g = "Bollinger Bands %B Filter"
        self.bb_tf = i.timeframe("30", "BB Timeframe", group=g)
        self.bb_period = i.int(20, "BB Period", minval=2, group=g)
        self.bb_dev = i.float(2.0, "BB Deviation", minval=0.1, step=0.1, group=g)
        self.bb_level = i.float(1.0, "BB %B Crossing Up Level", step=0.01, group=g)
        g = "RSI Filter"
        self.rsi_tf = i.timeframe("30", "RSI Timeframe", group=g)
        self.rsi_len = i.int(7, "RSI Length", minval=2, group=g)
        self.rsi_level = i.float(65.0, "RSI Crossing Up Level", minval=1, maxval=100, group=g)
        self.tp_pct = i.float(2.11, "Take Profit (%)", minval=0.1, step=0.01, group="Exit")
        g = "Backtest Window"
        self.use_date_filter = i.bool(True, "Limit Backtest Period", group=g)
        self.from_date = i.time(FROM_DATE, "From", group=g)
        self.to_date = i.time(TO_DATE, "To", group=g)
        self.base_entry = NA
        self.ao_filled = 0
        self.prev_pos = NA

    def bb_percent_b(self, v):
        basis = ta.sma(v.close, self.bb_period)
        dev = self.bb_dev * ta.stdev(v.close, self.bb_period)
        upper = basis + dev
        lower = basis - dev
        return div(v.close - lower, upper - lower)

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
        bb_b = self.security(None, self.bb_tf, lambda v: self.bb_percent_b(v), lookahead=False)
        rsi_val = self.security(None, self.rsi_tf, lambda v: ta.rsi(v.close, self.rsi_len), lookahead=False)
        bb_h, rsi_h = self.H("bb_b"), self.H("rsi_val")
        bb_b_1, rsi_val_1 = bb_h[1], rsi_h[1]
        bb_h.set(bb_b)
        rsi_h.set(rsi_val)
        bb_cross_up = bb_b_1 < self.bb_level and bb_b >= self.bb_level
        rsi_cross_up = rsi_val_1 < self.rsi_level and rsi_val >= self.rsi_level
        entry_cond = bool(bb_cross_up and rsi_cross_up)
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
                st.entry("Short_Base", st.short, qty=base_qty, limit=close, comment="Short_Base")
            else:
                st.entry("Short_Base", st.short, qty=base_qty, comment="Short_Base")
        if in_position and in_window and self.ao_filled < self.ao_count and not na(self.base_entry):
            next_idx = self.ao_filled + 1
            threshold = self.cum_dev(next_idx)
            trigger_px = self.base_entry * (1.0 + threshold / 100.0)
            if close >= trigger_px:
                ao_qty_usdt = self.ao_size_at(next_idx)
                st.entry("Short_AO_" + str(next_idx), st.short, qty=div(ao_qty_usdt, close), comment="Short_AO_" + str(next_idx))
                self.ao_filled = next_idx
        if in_position:
            avg_px = st.position_avg_price
            tp_price = avg_px * (1.0 - self.tp_pct / 100.0)
            if close <= tp_price:
                st.close_all(comment="TP")
        self.prev_pos = st.position_size

"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : RSI Oversold AO DCA — Long Strategy
Author       : 3Commas
Source URL   : https://www.tradingview.com/script/JtopWlYQ-RSI-Oversold-AO-Long-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation of a 3Commas DCA-bot template (orders processed at the bar close, process_orders_on_close). When the higher-timeframe RSI (request.security, lookahead off) crosses down through the level and no trade is open (inside the backtest window),
a base order of a fixed quote amount buys at the close (or as a limit order at the close when "Use LIMIT for Base" is on); up to N averaging orders (only while a second higher-timeframe RSI is below its own level) are added as the close falls through a geometric ladder of deviations from the base entry price (each step a multiple of the previous one)
with geometrically growing sizes; everything is closed at the bar close once the close reaches the take-profit percentage above the average entry price.
Deviations from the original: none.
Not carried over: the webhook alert text, AO ladder lines / labels, status table, watermark table and plots (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, nz, pmath, ta

FROM_DATE = 1769904000000     # timestamp("01 Feb 2026 00:00 +0000")
TO_DATE = 1780012740000       # timestamp("28 May 2026 23:59 +0000")


class RsiOversoldAoLong(Script):
    TITLE = "RSI Oversold AO DCA — Long Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="cash", default_qty_value=100, pyramiding=5, commission_type="percent",
                    commission_value=0.18, slippage=3, process_orders_on_close=True)
    SOURCE = {"id": "JtopWlYQ", "author": "3Commas", "licence": "not stated", "url": "https://www.tradingview.com/script/JtopWlYQ-RSI-Oversold-AO-Long-Strategy"}

    def init(self):
        i = self.input
        g = "Base Order"
        self.base_order_size = i.float(100.0, "Base Order Size (USDT)", minval=1, group=g)
        self.use_limit_base = i.bool(False, "Use LIMIT for Base (else Market)", group=g)
        g = "Averaging Orders"
        self.ao_count = i.int(4, "Averaging Orders per Trade", minval=0, maxval=10, group=g)
        self.ao_size = i.float(60.0, "First AO Size (USDT)", minval=1, group=g)
        self.ao_step = i.float(1.0, "Deviation to First AO (%)", minval=0.1, step=0.1, group=g)
        self.ao_step_mult = i.float(2.0, "Deviation Step Multiplier", minval=1.0, step=0.1, group=g)
        self.ao_size_mult = i.float(2.0, "Order Size Multiplier", minval=1.0, step=0.1, group=g)
        g = "Entry RSI Filter"
        self.entry_tf = i.timeframe("15", "RSI Timeframe", group=g)
        self.entry_rsi_len = i.int(7, "RSI Length", minval=2, group=g)
        self.entry_rsi_level = i.float(30.0, "RSI Crossing Down Level", minval=1, maxval=100, group=g)
        g = "AO Trigger RSI Filter"
        self.ao_rsi_tf = i.timeframe("15", "AO RSI Timeframe", group=g)
        self.ao_rsi_len = i.int(7, "AO RSI Length", minval=2, group=g)
        self.ao_rsi_level = i.float(25.0, "RSI Less Than", minval=1, maxval=100, group=g)
        self.tp_pct = i.float(3.0, "Take Profit (%)", minval=0.1, step=0.1, group="Exit")
        g = "Backtest Window"
        self.use_date_filter = i.bool(True, "Limit Backtest Period", group=g)
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
        rsi_h = self.H("entry_rsi")
        entry_rsi_1 = rsi_h[1]
        rsi_h.set(entry_rsi)
        entry_cond = bool(entry_rsi_1 > self.entry_rsi_level and entry_rsi <= self.entry_rsi_level)
        ao_rsi = self.security(None, self.ao_rsi_tf, lambda v: ta.rsi(v.close, self.ao_rsi_len), lookahead=False)
        cond_aog = ao_rsi < self.ao_rsi_level
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
        if in_position and in_window and self.ao_filled < self.ao_count and not na(self.base_entry) and cond_aog:
            next_idx = self.ao_filled + 1
            threshold = self.cum_dev(next_idx)
            trigger_px = self.base_entry * (1.0 - threshold / 100.0)
            if close <= trigger_px:
                ao_qty_usdt = self.ao_size_at(next_idx)
                st.entry("Long_AO_" + str(next_idx), st.long, qty=div(ao_qty_usdt, close), comment="Long_AO_" + str(next_idx))
                self.ao_filled = next_idx
        if in_position:
            avg_px = st.position_avg_price
            tp_price = avg_px * (1.0 + self.tp_pct / 100.0)
            if close >= tp_price:
                st.close_all(comment="TP")
        self.prev_pos = st.position_size

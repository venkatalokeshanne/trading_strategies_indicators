"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : INJ DCA Long Strategy [3Commas & QuantPilot]
Author       : 3Commas
Source URL   : https://www.tradingview.com/script/GM1bUrIF-INJ-DCA-Long-Strategy-3Commas-QuantPilot
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation of a 3Commas DCA-bot template. When the 240-minute RSI (request.security, lookahead off) is below 28.0 and no trade is open (inside the backtest window), a base order of 500 quote units buys at the
bar close (process_orders_on_close); averaging orders of increasing size are added as the close falls through fixed deviations from the base entry (up to 5, pyramiding 6); everything is closed at the bar close once the close reaches
9.0% above the average entry price. (Family member of 0wggzSk5; same logic, only title / RSI level / take-profit / end date differ.)

Deviations from the original: none.
Not carried over: the webhook alert text, AO ladder lines / labels, status table, watermark table and plots (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, na, nz, ta

FROM_DATE = 1704067200000     # timestamp("01 Jan 2024 00:00 +0000")
TO_DATE = 1783987140000       # timestamp("13 Jul 2026 23:59 +0000")


class ThreeCommasDcaGM1bUrIF(Script):
    TITLE = "INJ DCA Long Strategy [3Commas & QuantPilot]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="cash", default_qty_value=500, pyramiding=6, commission_type="percent",
                    commission_value=0.06, slippage=3, process_orders_on_close=True)
    SOURCE = {"id": "GM1bUrIF", "author": "3Commas", "licence": "not stated", "url": "https://www.tradingview.com/script/GM1bUrIF-INJ-DCA-Long-Strategy-3Commas-QuantPilot"}

    def init(self):
        g = "Base Order"
        self.base_order_size = self.input.float(500.0, "Base Order Size (USDT)", minval=1, group=g)
        self.use_limit_base = self.input.bool(False, "Use LIMIT for Base (else Market)", group=g)
        g = "Averaging Orders (Fixed Deviations + 1.8x Scaling)"
        self.ao_devs = [self.input.float(d, f"AO{k} Deviation from Base (%)", minval=0.1, step=0.1, group=g) for k, d in enumerate([2.0, 5.0, 9.5, 16.0, 25.0], 1)]
        self.ao_sizes = [self.input.float(z, f"AO{k} Size (USDT)", minval=1, group=g) for k, z in enumerate([900.0, 1620.0, 2916.0, 5249.0, 9448.0], 1)]
        g = "Entry Filters"
        self.rsi_tf = self.input.timeframe("240", "RSI Timeframe", group=g)
        self.rsi_len = self.input.int(14, "RSI Length", minval=2, group=g)
        self.rsi_level = self.input.float(28.0, "RSI Less Than", minval=1, maxval=100, group=g)
        self.tp_pct = self.input.float(9.0, "Take Profit (%)", minval=0.1, step=0.1, group="Exit")
        g = "Backtest Window"
        self.use_date_filter = self.input.bool(True, "Limit Backtest Period", group=g)
        self.from_date = self.input.time(FROM_DATE, "From", group=g)
        self.to_date = self.input.time(TO_DATE, "To", group=g)
        self.base_entry = NA
        self.ao_filled = 0
        self.prev_pos = NA

    def on_bar(self):
        in_window = (not self.use_date_filter) or (self.time >= self.from_date and self.time <= self.to_date)
        ao_count = 5
        rsi_val = self.security(None, self.rsi_tf, lambda v: ta.rsi(v.close, self.rsi_len))
        cond_rsi = rsi_val < self.rsi_level
        entry_signal = cond_rsi
        st = self.strategy
        in_position = st.position_size != 0
        just_entered = nz(self.prev_pos) == 0 and in_position
        position_just_flat = nz(self.prev_pos) != 0 and not in_position
        if just_entered and na(self.base_entry):
            self.base_entry = st.position_avg_price
            self.ao_filled = 0
        if position_just_flat or not in_position:
            self.base_entry = NA
            self.ao_filled = 0
        open_base = in_window and (not in_position) and st.opentrades == 0 and entry_signal
        if open_base:
            base_qty = div(self.base_order_size, self.close)
            st.entry("Long_Base", st.long, qty=base_qty, comment="Long_Base")
        if in_position and in_window and self.ao_filled < ao_count and not na(self.base_entry):
            next_idx = self.ao_filled + 1
            threshold = self.ao_devs[next_idx - 1]
            trigger_px = self.base_entry * (1.0 - threshold / 100.0)
            if self.close <= trigger_px:
                ao_usdt = self.ao_sizes[next_idx - 1]
                st.entry("Long_AO_" + str(next_idx), st.long, qty=div(ao_usdt, self.close), comment="Long_AO_" + str(next_idx))
                self.ao_filled = next_idx
        if in_position:
            avg_px = st.position_avg_price
            tp_price = avg_px * (1.0 + self.tp_pct / 100.0)
            if self.close >= tp_price:
                st.close_all(comment="TP")
        self.plot(st.position_avg_price if in_position else NA, "Avg Entry", color=color.orange, linewidth=2)
        self.prev_pos = st.position_size

"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : AMZN RSI Oversold Doubling DCA — Long Strategy
Author       : 3Commas
Source URL   : https://www.tradingview.com/script/kuuXl2Gc-3Commas-AMZN-RSI-Oversold-Doubling-DCA-Long-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation of a 3Commas DCA-bot template (orders processed at the bar close, process_orders_on_close). When the higher-timeframe RSI (request.security, lookahead off) is below the level and no trade is open (inside the backtest window),
a base order of a fixed quote amount buys at the close (or as a limit order at the close when "Use LIMIT for Base" is on); up to N averaging orders are added as the close falls through a fixed ladder of deviations from the base entry price with fixed sizes (doubling); everything is closed at the bar close once the close reaches the take-profit percentage above the average entry price.
Deviations from the original: none.
Not carried over: the webhook alert text, AO ladder lines / labels, status table, watermark table and plots (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, nz, ta

FROM_DATE = 1704067200000     # timestamp("01 Jan 2024 00:00 +0000 +0000")
TO_DATE = 1780617540000       # timestamp("04 Jun 2026 23:59 +0000 +0000")


class RsiDoublingDcaLongkuuXl2Gc(Script):
    TITLE = "AMZN RSI Oversold Doubling DCA — Long Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="cash", default_qty_value=500, pyramiding=6, commission_type="percent",
                    commission_value=0.06, slippage=3, process_orders_on_close=True)
    SOURCE = {"id": "kuuXl2Gc", "author": "3Commas", "licence": "not stated", "url": "https://www.tradingview.com/script/kuuXl2Gc-3Commas-AMZN-RSI-Oversold-Doubling-DCA-Long-Strategy"}

    def init(self):
        i = self.input
        g = "Base Order"
        self.base_order_size = i.float(500.0, "Base Order Size (USDT)", minval=1, group=g)
        self.use_limit_base = i.bool(False, "Use LIMIT for Base (else Market)", group=g)
        g = "Averaging Orders"
        self.ao_devs = [i.float(d, f"AO{k} Deviation from Base (%)", minval=0.1, step=0.1, group=g) for k, d in enumerate([2.0, 5.0, 9.5, 16.0, 25.0], 1)]
        self.ao_sizes = [i.float(z, f"AO{k} Size (USDT)", minval=1, group=g) for k, z in enumerate([1000.0, 2000.0, 4000.0, 8000.0, 16000.0], 1)]
        self.ao_count = 5
        g = "Entry RSI Filter"
        self.entry_tf = i.timeframe("240", "RSI Timeframe", group=g)
        self.entry_rsi_len = i.int(14, "RSI Length", minval=2, group=g)
        self.entry_rsi_level = i.float(28.0, "RSI Less Than", minval=1, maxval=100, group=g)
        self.tp_pct = i.float(3.0, "Take Profit (%)", minval=0.1, step=0.1, group="Exit")
        g = "Backtest Window"
        self.use_date_filter = i.bool(True, "Limit Backtest Period", group=g)
        self.from_date = i.time(FROM_DATE, "From", group=g)
        self.to_date = i.time(TO_DATE, "To", group=g)
        self.base_entry = NA
        self.ao_filled = 0
        self.prev_pos = NA

    def on_bar(self):
        st = self.strategy
        close = self.close
        in_window = (not self.use_date_filter) or (self.time >= self.from_date and self.time <= self.to_date)
        entry_rsi = self.security(None, self.entry_tf, lambda v: ta.rsi(v.close, self.entry_rsi_len), lookahead=False)
        entry_cond = entry_rsi < self.entry_rsi_level
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
            threshold = self.ao_devs[next_idx - 1]
            trigger_px = self.base_entry * (1.0 - threshold / 100.0)
            if close <= trigger_px:
                ao_qty_usdt = self.ao_sizes[next_idx - 1]
                st.entry("Long_AO_" + str(next_idx), st.long, qty=div(ao_qty_usdt, close), comment="Long_AO_" + str(next_idx))
                self.ao_filled = next_idx
        if in_position:
            avg_px = st.position_avg_price
            tp_price = avg_px * (1.0 + self.tp_pct / 100.0)
            if close >= tp_price:
                st.close_all(comment="TP")
        self.prev_pos = st.position_size

"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : [3Commas] SOL RSI Reversal DCA - Short Strategy
Author       : 3Commas
Source URL   : https://www.tradingview.com/script/ZNXTGgKN-3Commas-SOL-RSI-Reversal-DCA-Short-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation of a 3Commas DCA-bot template (orders processed at the bar close, process_orders_on_close). When the higher-timeframe RSI (request.security, lookahead off) crosses down through the level and no trade is open (inside the backtest window),
a base order of a fixed quote amount sells short at the close (or as a limit order at the close when "Use LIMIT for Base" is on); up to N averaging orders are added as the close rises through a geometric ladder of deviations from the base entry price (each step a multiple of the previous one)
with geometrically growing sizes; a hard stop closes everything at the bar close when the close reaches the stop percentage above the average entry price; once the close has reached the take-profit percentage below it, a trailing exit follows the lowest close and closes everything when the close retraces by the trailing percentage.
Deviations from the original: none.
Not carried over: the webhook alert text, AO ladder lines / labels, status table, watermark table and plots (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, nz, pmath, ta

FROM_DATE = 1772496000000     # timestamp("03 Mar 2026 00:00 +0000")
TO_DATE = 1780790340000       # timestamp("06 Jun 2026 23:59 +0000")


class ThreeCommasRsiShortZNXTGgKN(Script):
    TITLE = "[3Commas] SOL RSI Reversal DCA - Short Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="cash", default_qty_value=500, pyramiding=4, commission_type="percent",
                    commission_value=0.06, slippage=3, process_orders_on_close=True)
    SOURCE = {"id": "ZNXTGgKN", "author": "3Commas", "licence": "not stated", "url": "https://www.tradingview.com/script/ZNXTGgKN-3Commas-SOL-RSI-Reversal-DCA-Short-Strategy"}

    def init(self):
        i = self.input
        g = "Base Order"
        self.base_order_size = i.float(500.0, "Base Order Size (USDT)", minval=1, group=g)
        self.use_limit_base = i.bool(True, "Use LIMIT for Base (else Market)", group=g)
        g = "Averaging Orders"
        self.ao_count = i.int(3, "Averaging Orders per Trade", minval=0, maxval=10, group=g)
        self.ao_size = i.float(250.0, "First AO Size (USDT)", minval=1, group=g)
        self.ao_step = i.float(1.0, "Deviation to First AO (%)", minval=0.1, step=0.1, group=g)
        self.ao_step_mult = i.float(1.0, "Deviation Step Multiplier", minval=1.0, step=0.1, group=g)
        self.ao_size_mult = i.float(1.0, "Order Size Multiplier", minval=1.0, step=0.05, group=g)
        g = "Trade Start Condition (RSI Crossing Down)"
        self.entry_tf = i.timeframe("3", "RSI Timeframe", group=g)
        self.entry_rsi_len = i.int(9, "RSI Length", minval=2, group=g)
        self.entry_rsi_level = i.float(80.0, "RSI Crossing Down Level", minval=1, maxval=100, group=g)
        self.tp_pct = i.float(1.3, "Take Profit (%)", minval=0.1, step=0.1, group="Exit")
        self.trail_pct = i.float(0.3, "Trailing (%)", minval=0.1, step=0.1, group="Exit")
        self.sl_pct = i.float(8.0, "Stop Loss (%)", minval=0.1, step=0.1, group="Exit")
        g = "Backtest Window"
        self.use_date_filter = i.bool(True, "Limit Backtest Period", group=g)
        self.from_date = i.time(FROM_DATE, "From", group=g)
        self.to_date = i.time(TO_DATE, "To", group=g)
        self.base_entry = NA
        self.ao_filled = 0
        self.prev_pos = NA
        self.min_since_tp = NA
        self.in_tp_zone = False

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
        rsi_cross_dn = self.security(None, self.entry_tf, lambda v: ta.crossunder(ta.rsi(v.close, self.entry_rsi_len), self.entry_rsi_level), lookahead=False)
        entry_cond = rsi_cross_dn == 1
        in_position = st.position_size != 0
        just_entered = nz(self.prev_pos) == 0 and in_position
        position_just_flat = nz(self.prev_pos) != 0 and not in_position
        if just_entered and na(self.base_entry):
            self.base_entry = st.position_avg_price
            self.ao_filled = 0
        if position_just_flat or not in_position:
            self.base_entry = NA
            self.ao_filled = 0
            self.min_since_tp = NA
            self.in_tp_zone = False
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
            sl_price = avg_px * (1.0 + self.sl_pct / 100.0)
            tp_price = avg_px * (1.0 - self.tp_pct / 100.0)
            if close >= sl_price:
                st.close_all(comment="SL")
            else:
                if close <= tp_price:
                    self.in_tp_zone = True
                    self.min_since_tp = float(close) if na(self.min_since_tp) else pmath.min(self.min_since_tp, close)
                if self.in_tp_zone:
                    trail_stop = self.min_since_tp * (1.0 + self.trail_pct / 100.0)
                    if close >= trail_stop:
                        st.close_all(comment="TP_Trail")
        self.prev_pos = st.position_size

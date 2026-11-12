"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : RSI Dip + EMA Trend Long DCA — Leveraged Strategy
Author       : 3Commas
Source URL   : https://www.tradingview.com/script/Tl9RRJAT-RSI-Dip-EMA-Trend-Long-DCA-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation of a 3Commas DCA-bot template (orders processed at the bar close, process_orders_on_close). When the higher-timeframe RSI (request.security, lookahead off) has crossed down through the level while a higher-timeframe fast EMA is above its slow EMA and no trade is open (inside the backtest window),
a base order of margin x leverage quote units buys at the close (or as a limit order at the close when "Use LIMIT for Base" is on); up to N safety orders are added as the close falls through a geometric ladder of deviations from the base entry price (each step a multiple of the previous one)
with geometrically growing margins; a hard stop below the average entry price and a maximum holding time close everything at the bar close, and once the close reaches the take-profit percentage above the average a trailing exit follows the highest close and closes everything when the close retraces by the trailing deviation.
Deviations from the original: none.
Not carried over: the webhook alert text, AO ladder lines / labels, status table, watermark table and plots (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, nz, pmath, ta

FROM_DATE = 1706659200000     # timestamp("31 Jan 2024 00:00 +0000")
TO_DATE = 1767743940000       # timestamp("06 Jan 2026 23:59 +0000")


class RsiDipEmaTrendLong(Script):
    TITLE = "RSI Dip + EMA Trend Long DCA — Leveraged Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="cash", default_qty_value=1500, pyramiding=5, commission_type="percent",
                    commission_value=0.05, slippage=3, process_orders_on_close=True)
    SOURCE = {"id": "Tl9RRJAT", "author": "3Commas", "licence": "not stated", "url": "https://www.tradingview.com/script/Tl9RRJAT-RSI-Dip-EMA-Trend-Long-DCA-Strategy"}

    def init(self):
        i = self.input
        g = "Base Order"
        self.base_margin = i.float(60.0, "Base Order Margin (USDT)", minval=1, group=g)
        self.leverage = i.float(25.0, "Leverage (×)", minval=1.0, maxval=100.0, step=1.0, group=g)
        self.use_limit_base = i.bool(False, "Use LIMIT for Base (else Market)", group=g)
        g = "Safety Orders"
        self.so_count = i.int(4, "Max Safety Orders", minval=0, maxval=10, group=g)
        self.so_margin = i.float(60.0, "First SO Margin (USDT)", minval=1, group=g)
        self.so_step = i.float(1.0, "Step to First SO (%)", minval=0.1, step=0.1, group=g)
        self.so_step_mult = i.float(1.2, "Step Multiplier", minval=1.0, step=0.05, group=g)
        self.so_size_mult = i.float(1.05, "Size Multiplier", minval=1.0, step=0.01, group=g)
        g = "Entry RSI Filter (Oversold Dip)"
        self.entry_tf = i.timeframe("5", "RSI Timeframe", group=g)
        self.entry_rsi_len = i.int(12, "RSI Length", minval=2, group=g)
        self.entry_rsi_level = i.float(35.0, "RSI Crossing Down Level", minval=1, maxval=100, group=g)
        g = "EMA Trend Filter"
        self.ema_tf = i.timeframe("15", "EMA Timeframe", group=g)
        self.ema_fast = i.int(50, "Fast EMA Length", minval=2, group=g)
        self.ema_slow = i.int(100, "Slow EMA Length", minval=2, group=g)
        g = "Exit"
        self.tp_pct = i.float(1.0, "Take Profit (%)", minval=0.1, step=0.1, group=g)
        self.trail_dev = i.float(0.1, "Trailing Deviation (%)", minval=0.05, step=0.05, group=g)
        self.sl_pct = i.float(9.0, "Stop Loss (%)", minval=0.1, step=0.1, group=g)
        g = "Max Hold Period"
        self.use_max_hold = i.bool(True, "Force Close After Max Hold", group=g)
        self.max_hold_seconds = i.int(259200, "Max Hold (seconds)", minval=60, group=g)
        g = "Backtest Window"
        self.use_date_filter = i.bool(True, "Limit Backtest Period", group=g)
        self.from_date = i.time(FROM_DATE, "From", group=g)
        self.to_date = i.time(TO_DATE, "To", group=g)
        self.base_entry = NA
        self.ao_filled = 0
        self.prev_pos = NA
        self.trailing_peak = NA
        self.in_tp_zone = False
        self.entry_time = NA

    def cum_dev(self, k):
        dev = 0.0
        step = self.so_step
        for j in range(1, k + 1):
            if j == 1:
                dev = step
            else:
                step = step * self.so_step_mult
                dev = dev + step
        return dev

    def so_margin_at(self, k):
        return self.so_margin * pmath.pow(self.so_size_mult, k - 1)

    def on_bar(self):
        st = self.strategy
        close = self.close
        in_window = (not self.use_date_filter) or (self.time >= self.from_date and self.time <= self.to_date)
        entry_rsi = self.security(None, self.entry_tf, lambda v: ta.rsi(v.close, self.entry_rsi_len), lookahead=False)
        rsi_h = self.H("entry_rsi")
        entry_rsi_1 = rsi_h[1]
        rsi_h.set(entry_rsi)
        entry_cross_down = bool(entry_rsi_1 > self.entry_rsi_level and entry_rsi <= self.entry_rsi_level)
        ema_fast_val = self.security(None, self.ema_tf, lambda v: ta.ema(v.close, self.ema_fast), lookahead=False)
        ema_slow_val = self.security(None, self.ema_tf, lambda v: ta.ema(v.close, self.ema_slow), lookahead=False)
        cond_trend = ema_fast_val > ema_slow_val
        entry_cond = bool(entry_cross_down and cond_trend)
        in_position = st.position_size != 0
        just_entered = nz(self.prev_pos) == 0 and in_position
        position_just_flat = nz(self.prev_pos) != 0 and not in_position
        if just_entered and na(self.base_entry):
            self.base_entry = st.position_avg_price
            self.ao_filled = 0
            self.trailing_peak = NA
            self.in_tp_zone = False
            self.entry_time = float(self.time)
        if position_just_flat or not in_position:
            self.base_entry = NA
            self.ao_filled = 0
            self.trailing_peak = NA
            self.in_tp_zone = False
            self.entry_time = NA
        open_base = in_window and (not in_position) and st.opentrades == 0 and entry_cond
        if open_base:
            base_qty = div(self.base_margin * self.leverage, close)
            if self.use_limit_base:
                st.entry("Long_Base", st.long, qty=base_qty, limit=close, comment="Long_Base")
            else:
                st.entry("Long_Base", st.long, qty=base_qty, comment="Long_Base")
        if in_position and in_window and self.ao_filled < self.so_count and not na(self.base_entry):
            next_idx = self.ao_filled + 1
            threshold = self.cum_dev(next_idx)
            trigger_px = self.base_entry * (1.0 - threshold / 100.0)
            if close <= trigger_px:
                so_notional = self.so_margin_at(next_idx) * self.leverage
                st.entry("Long_SO_" + str(next_idx), st.long, qty=div(so_notional, close), comment="Long_SO_" + str(next_idx))
                self.ao_filled = next_idx
        closed_this_bar = False
        if in_position:
            avg_px = st.position_avg_price
            tp_price = avg_px * (1.0 + self.tp_pct / 100.0)
            sl_price = avg_px * (1.0 - self.sl_pct / 100.0)
            if close <= sl_price:
                st.close_all(comment="SL")
                closed_this_bar = True
            if (not closed_this_bar) and self.use_max_hold and not na(self.entry_time):
                hold_ms = self.time - self.entry_time
                if hold_ms >= self.max_hold_seconds * 1000:
                    st.close_all(comment="MaxHold")
                    closed_this_bar = True
            if not closed_this_bar:
                if close >= tp_price:
                    self.in_tp_zone = True
                    self.trailing_peak = float(close) if na(self.trailing_peak) else pmath.max(self.trailing_peak, close)
                if self.in_tp_zone and not na(self.trailing_peak):
                    trail_stop = self.trailing_peak * (1.0 - self.trail_dev / 100.0)
                    if close <= trail_stop:
                        st.close_all(comment="TP_Trail")
                        closed_this_bar = True
        self.prev_pos = st.position_size

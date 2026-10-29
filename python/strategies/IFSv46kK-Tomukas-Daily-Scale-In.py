"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Tomukas Sweep Reclaim Scale-In Strategy
Author       : Tomukasss
Source URL   : https://www.tradingview.com/script/IFSv46kK-Tomukas-Daily-Scale-In
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close: orders fill at the signal bar's close). Swing highs / lows (8 bars each side) are swept when a later bar's extreme goes beyond them by between a minimum and a maximum ATR fraction; within the reclaim window a close back through the swept level (by a buffer, with a strong close location and body, on the right side of the 200 EMA)
is a reclaim signal. A buy reclaim opens a long of 10 % of equity (closing an opposite position first), a sell reclaim a short. While the trade runs, up to four scale-in entries (10 / 20 / 40 / 80 % of equity) are added each time the low (high) reaches a further step percentage from the first entry price; the whole position is closed when the high (low) reaches the
take-profit percentage from the average price.
Deviations from the original: none.
Not carried over: nothing (no display code in the source).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, nz, pmath, ta


class SweepReclaimScaleIn(Script):
    TITLE = "Tomukas Sweep Reclaim Scale-In Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=5, process_orders_on_close=True, initial_capital=10000, commission_type="percent", commission_value=0.05)
    SOURCE = {"id": "IFSv46kK", "author": "Tomukasss", "licence": "not stated", "url": "https://www.tradingview.com/script/IFSv46kK-Tomukas-Daily-Scale-In"}

    def init(self):
        i = self.input
        self.left_bars = i.int(8, "Swing Left", minval=1)
        self.right_bars = i.int(8, "Swing Right", minval=1)
        self.atr_len = i.int(14, "ATR Length")
        self.min_sweep_atr = i.float(0.05, "Min Sweep ATR", step=0.01)
        self.max_sweep_atr = i.float(0.80, "Max Sweep ATR", step=0.01)
        self.reclaim_bars = i.int(3, "Reclaim Window Bars", minval=0)
        self.close_buffer_atr = i.float(0.02, "Reclaim Close Buffer ATR", step=0.01)
        self.min_close_location = i.float(0.60, "Min Close Location", step=0.05)
        self.min_body_atr = i.float(0.05, "Min Body ATR", step=0.01)
        self.use_ema = i.bool(True, "Use EMA200 Bias")
        self.ema_len = i.int(200, "EMA Length")
        self.tp_pct = i.float(0.40, "Take Profit Fixed % From Average", step=0.05)
        self.scale_step_pct = i.float(0.30, "Scale-In Step Fixed %", step=0.05)
        self.q = [i.float(v, "Entry %d %% Equity" % (k + 1)) for k, v in enumerate((10, 10, 20, 40, 80))]
        self.close_on_opposite = i.bool(True, "Close On Opposite Signal")
        self.swing_high = NA
        self.swing_low = NA
        self.swing_high_bar = NA
        self.swing_low_bar = NA
        self.high_swept = False
        self.low_swept = False
        self.high_sweep_bar = NA
        self.low_sweep_bar = NA
        self.high_sweep_level = NA
        self.low_sweep_level = NA
        self.scale_stage = 0
        self.base_entry = NA
        self.trade_dir = 0

    def f_qty(self, pct):
        return div(self.strategy.equity * pct / 100.0, self.close)

    def f_scale_qty(self, stage):
        return self.q[min(stage, 5) - 1]

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        bar_index = self.bar_index
        atr = ta.atr(self.atr_len)
        safe_atr = pmath.max(nz(atr), self.syminfo.mintick)
        ema = ta.ema(close, self.ema_len)
        bull_bias = (not self.use_ema) or close > ema
        bear_bias = (not self.use_ema) or close < ema
        body_atr = div(abs(close - open_), safe_atr)
        bar_range = pmath.max(high - low, self.syminfo.mintick)
        bull_close_location = div(close - low, bar_range)
        bear_close_location = div(high - close, bar_range)
        ph = ta.pivothigh(high, self.left_bars, self.right_bars)
        pl = ta.pivotlow(low, self.left_bars, self.right_bars)
        if not na(ph):
            self.swing_high = ph
            self.swing_high_bar = bar_index - self.right_bars
            self.high_swept = False
        if not na(pl):
            self.swing_low = pl
            self.swing_low_bar = bar_index - self.right_bars
            self.low_swept = False
        high_sweep_depth = div(high - self.swing_high, safe_atr) if not na(self.swing_high) else NA
        low_sweep_depth = div(self.swing_low - low, safe_atr) if not na(self.swing_low) else NA
        new_high_sweep = (not na(self.swing_high)) and (not self.high_swept) and bar_index > self.swing_high_bar and high > self.swing_high \
            and high_sweep_depth >= self.min_sweep_atr and high_sweep_depth <= self.max_sweep_atr
        new_low_sweep = (not na(self.swing_low)) and (not self.low_swept) and bar_index > self.swing_low_bar and low < self.swing_low \
            and low_sweep_depth >= self.min_sweep_atr and low_sweep_depth <= self.max_sweep_atr
        if new_high_sweep:
            self.high_swept = True
            self.high_sweep_bar = bar_index
            self.high_sweep_level = self.swing_high
        if new_low_sweep:
            self.low_swept = True
            self.low_sweep_bar = bar_index
            self.low_sweep_level = self.swing_low
        sell_reclaim = self.high_swept and (not na(self.high_sweep_bar)) and bar_index - self.high_sweep_bar <= self.reclaim_bars \
            and close < self.high_sweep_level - safe_atr * self.close_buffer_atr and bear_close_location >= self.min_close_location \
            and body_atr >= self.min_body_atr and bear_bias
        buy_reclaim = self.low_swept and (not na(self.low_sweep_bar)) and bar_index - self.low_sweep_bar <= self.reclaim_bars \
            and close > self.low_sweep_level + safe_atr * self.close_buffer_atr and bull_close_location >= self.min_close_location \
            and body_atr >= self.min_body_atr and bull_bias
        if sell_reclaim:
            self.high_swept = False
        if buy_reclaim:
            self.low_swept = False
        if sell_reclaim and buy_reclaim:
            sell_reclaim = False
            buy_reclaim = False
        flat = st.position_size == 0
        if flat:
            self.scale_stage = 0
            self.base_entry = NA
            self.trade_dir = 0
        if buy_reclaim and (flat or st.position_size < 0):
            if st.position_size < 0 and self.close_on_opposite:
                st.close_all(comment="Close Short")
            st.entry("L1", st.long, qty=self.f_qty(self.q[0]))
            self.base_entry = float(close)
            self.scale_stage = 1
            self.trade_dir = 1
        if sell_reclaim and (flat or st.position_size > 0):
            if st.position_size > 0 and self.close_on_opposite:
                st.close_all(comment="Close Long")
            st.entry("S1", st.short, qty=self.f_qty(self.q[0]))
            self.base_entry = float(close)
            self.scale_stage = 1
            self.trade_dir = -1
        if st.position_size > 0 and self.trade_dir == 1 and self.scale_stage > 0 and self.scale_stage < 5:
            next_add_price_long = self.base_entry * (1 - self.scale_step_pct * self.scale_stage / 100)
            if low <= next_add_price_long:
                self.scale_stage += 1
                st.entry("L" + str(self.scale_stage), st.long, qty=self.f_qty(self.f_scale_qty(self.scale_stage)))
        if st.position_size < 0 and self.trade_dir == -1 and self.scale_stage > 0 and self.scale_stage < 5:
            next_add_price_short = self.base_entry * (1 + self.scale_step_pct * self.scale_stage / 100)
            if high >= next_add_price_short:
                self.scale_stage += 1
                st.entry("S" + str(self.scale_stage), st.short, qty=self.f_qty(self.f_scale_qty(self.scale_stage)))
        long_tp = st.position_avg_price * (1 + self.tp_pct / 100)
        short_tp = st.position_avg_price * (1 - self.tp_pct / 100)
        if st.position_size > 0 and high >= long_tp:
            st.close_all(comment="TP Long")
        if st.position_size < 0 and low <= short_tp:
            st.close_all(comment="TP Short")

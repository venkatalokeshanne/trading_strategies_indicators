"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Asia Liquidity Sweep Reversal Scalper (GC/Gold) [Strategy]
Author       : bradenstrock
Source URL   : https://www.tradingview.com/script/4IevbowH-Asia-Liquidity-Sweep-Reversal-Scalper-GC-Gold-Strategy
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Pivots (3 bars each side) keep the last pivot high / low; inside the Asia session (19:00-00:00 New York
time, bar start) a bar that sweeps below the last pivot low and closes back above it with RSI(14) at most 45 goes long when flat
(sweep above the last pivot high with RSI at least 55: short). Both strategy.exit calls are unconditional (stop 1.2 ATR / target
1.4 ATR around strategy.position_avg_price), so bar i works with the levels computed at bar i-1's close: none on a fill bar.
entryBarIndex is set on the first bar a position is open at the close; 25 bars later everything is closed at the next open.

Deviations from the original: none.
Not carried over: the pivot-level plots and the session background (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, ta


class AsiaSweepScalper(Script):
    TITLE = "Asia Liquidity Sweep Reversal Scalper (GC/Gold) [Strategy]"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, initial_capital=10000)
    SOURCE = {"id": "4IevbowH", "author": "bradenstrock", "licence": "not stated",
              "url": "https://www.tradingview.com/script/4IevbowH-Asia-Liquidity-Sweep-Reversal-Scalper-GC-Gold-Strategy"}

    def init(self):
        self.session_str = self.input.session("1900-0000", "Asia Session (New York time)")
        self.use_session = self.input.bool(True, "Restrict trades to Asia session")
        self.pivot_left = self.input.int(3, "Pivot Left Bars", minval=1, maxval=20)
        self.pivot_right = self.input.int(3, "Pivot Right Bars", minval=1, maxval=20)
        self.rsi_len = self.input.int(14, "RSI Length", minval=1)
        self.rsi_max_long = self.input.int(45, "Max RSI for Long (avoid chasing)", minval=1, maxval=99)
        self.rsi_min_short = self.input.int(55, "Min RSI for Short (avoid chasing)", minval=1, maxval=99)
        self.atr_len = self.input.int(14, "ATR Length", minval=1)
        self.sl_atr = self.input.float(1.2, "Stop Loss (ATR multiple)", step=0.1)
        self.tp_atr = self.input.float(1.4, "Take Profit (ATR multiple)", step=0.1)
        self.use_time_exit = self.input.bool(True, "Time-based exit (bars)")
        self.max_hold_bars = self.input.int(25, "Max bars to hold", minval=1, maxval=500)
        self.last_ph = NA
        self.last_pl = NA
        self.entry_bar_index = NA

    def on_bar(self):
        in_session = not na(self.time_fn(None, self.session_str, "America/New_York"))
        trade_ok = in_session if self.use_session else True
        ph = ta.pivothigh(self.high, self.pivot_left, self.pivot_right)
        pl = ta.pivotlow(self.low, self.pivot_left, self.pivot_right)
        if not na(ph):
            self.last_ph = ph
        if not na(pl):
            self.last_pl = pl
        rsi = ta.rsi(self.close, self.rsi_len)
        atr = ta.atr(self.atr_len)
        st = self.strategy
        sweep_down = trade_ok and not na(self.last_pl) and self.low < self.last_pl and self.close > self.last_pl
        long_ok = sweep_down and rsi <= self.rsi_max_long and st.position_size == 0
        sweep_up = trade_ok and not na(self.last_ph) and self.high > self.last_ph and self.close < self.last_ph
        short_ok = sweep_up and rsi >= self.rsi_min_short and st.position_size == 0
        if long_ok:
            st.entry("L", st.long)
        if short_ok:
            st.entry("S", st.short)
        avg = st.position_avg_price
        st.exit("LX", from_entry="L", stop=avg - self.sl_atr * atr, limit=avg + self.tp_atr * atr)
        st.exit("SX", from_entry="S", stop=avg + self.sl_atr * atr, limit=avg - self.tp_atr * atr)
        if st.position_size != 0 and na(self.entry_bar_index):
            self.entry_bar_index = self.bar_index
        if st.position_size == 0:
            self.entry_bar_index = NA
        held_bars = (self.bar_index - self.entry_bar_index) if st.position_size != 0 else 0
        if self.use_time_exit and st.position_size != 0 and held_bars >= self.max_hold_bars:
            st.close_all(comment="Time Exit")
        self.plot(self.last_ph, "Last Pivot High")
        self.plot(self.last_pl, "Last Pivot Low")

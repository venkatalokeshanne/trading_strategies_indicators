"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Compression Breakout System
Author       : mateosandoval1025
Source URL   : https://www.tradingview.com/script/97gxVA5b-Compression-Breakout-System
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). A Bollinger width in the lowest percent-rank of the last 126 bars within the last few bars, a close above the previous
20-bar high on above-average volume and above the SMA200 buys with a risk-sized quantity. The script keeps a high-water mark of closes and closes the position when the
close falls below the larger of the entry stop (ATR multiple below the entry close) and a chandelier trail (high-water mark minus an ATR multiple), or after the window end.

Deviations from the original: none.
Not carried over: the band plots and fill, stop plot, BRK label, squeeze background and the info table (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, na, pmath, ta

START_T = 1104537600000     # 1 Jan 2005 00:00 +0000
END_T = 4070908800000       # 1 Jan 2099 00:00 +0000


class CompressionBreakout(Script):
    TITLE = "Compression Breakout System"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100, commission_type="percent",
                    commission_value=0.05, slippage=1, process_orders_on_close=True)
    SOURCE = {"id": "97gxVA5b", "author": "mateosandoval1025", "licence": "not stated",
              "url": "https://www.tradingview.com/script/97gxVA5b-Compression-Breakout-System"}

    def init(self):
        self.bb_len = self.input.int(20, "Bollinger length", minval=5)
        self.bb_mult = self.input.float(2.0, "Bollinger mult", minval=0.5, step=0.25)
        self.rank_len = self.input.int(126, "Width rank window (days)", minval=30)
        self.sqz_pct = self.input.float(25.0, "Squeeze: width %-rank below", minval=5, maxval=50, step=5.0)
        self.sqz_age = self.input.int(5, "Breakout within N bars of squeeze", minval=1)
        self.brk_len = self.input.int(20, "Breakout lookback (days)", minval=5)
        self.sma_len = self.input.int(200, "Trend SMA length", minval=50)
        self.atr_len = self.input.int(22, "ATR length", minval=5)
        self.stop_atr = self.input.float(2.0, "Initial stop (x ATR)", minval=0.5, step=0.25)
        self.risk_pct = self.input.float(4.0, "Risk per trade (% of equity)", minval=0.25, maxval=10.0, step=0.25)
        self.start_t = self.input.time(START_T, "Backtest start")
        self.end_t = self.input.time(END_T, "Backtest end")
        self.trail_atr = self.input.float(3.0, "Chandelier trail (x ATR)", minval=1.0, step=0.25)
        self.entry_stop = NA
        self.hwm = NA

    def on_bar(self):
        basis = ta.sma(self.close, self.bb_len)
        dev = ta.stdev(self.close, self.bb_len) * self.bb_mult
        bb_w = div(2.0 * dev, basis) * 100.0
        w_rank = ta.percentrank(bb_w, self.rank_len)
        sqz_on = w_rank < self.sqz_pct
        sqz_recent = ta.msum(1 if sqz_on else 0, self.sqz_age) > 0
        brk_lvl = self.H("brk")[1]
        self.H("brk").set(ta.highest(self.high, self.brk_len))
        vol_ok = self.volume > ta.sma(self.volume, 20)
        atr = ta.atr(self.atr_len)
        sma_t = ta.sma(self.close, self.sma_len)
        trend_ok = self.close > sma_t
        st = self.strategy
        in_pos = st.position_size > 0
        buy_sig = (not in_pos) and self.time >= self.start_t and self.time <= self.end_t and sqz_recent and self.close > brk_lvl and vol_ok and trend_ok
        if buy_sig:
            stop_dist = atr * self.stop_atr
            qty = pmath.min(div(st.equity * self.risk_pct / 100.0, stop_dist), div(st.equity, self.close))
            st.entry("Long", st.long, qty=qty)
            self.entry_stop = self.close - stop_dist
            self.hwm = float(self.close)
        if in_pos:
            self.hwm = pmath.max(self.hwm, self.close)
        if in_pos and self.time > self.end_t:
            st.close("Long", comment="window end")
        stop_lvl = pmath.max(self.entry_stop, self.hwm - atr * self.trail_atr)
        if in_pos and self.close < stop_lvl:
            st.close("Long", comment="stop: failed break" if self.close <= self.entry_stop else "exit: trail")
        self.plot(basis, "BB basis", color=color.gray)
        self.plot(stop_lvl if in_pos else NA, "Stop/Trail", color=color.yellow)
        self.plot(sma_t, "Trend SMA", color=color.green if trend_ok else color.red, linewidth=2)

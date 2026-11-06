"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Mpatel RSI 2-Entry (Futures Ready)
Author       : mpatel3559
Source URL   : https://www.tradingview.com/script/5LYHXbqi-Mpatel-RSI-2-Entry-stock-etf-future
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. Long only with two entries (pyramiding 2): when flat, the RSI crossing under the oversold level with the close at or below the limit price opens "Buy1"; once it is filled, a second RSI oversold cross with the close at or below a level `Entry 2 Drop` percent under the first fill opens "Buy2".
A take-profit (and optional stop) around the average price is re-issued for both entries at every bar of the position; the RSI crossing over the overbought level closes everything at the next open.

Deviations from the original: none.
Not carried over: the dashboard table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, ta


class MpatelRsi2Entry(Script):
    TITLE = "Mpatel RSI 2-Entry (Futures Ready)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="fixed", default_qty_value=1, commission_type="cash_per_contract", commission_value=0.62, slippage=2, pyramiding=2)
    SOURCE = {"id": "5LYHXbqi", "author": "mpatel3559", "licence": "not stated",
              "url": "https://www.tradingview.com/script/5LYHXbqi-Mpatel-RSI-2-Entry-stock-etf-future"}

    def init(self):
        i = self.input
        g = "RSI Settings"
        self.rsi_len = i.int(14, "RSI Length", minval=1, maxval=100, group=g)
        self.rsi_src = i.source(self.close, "RSI Source", group=g)
        self.oversold = i.int(30, "Oversold Level", minval=1, maxval=49, group=g)
        self.overbought = i.int(70, "Overbought Level", minval=51, maxval=99, group=g)
        g = "Entry Settings"
        self.limit_price = i.float(1, "Limit Buy Price", minval=0.01, step=0.25, group=g)
        self.dca_pct = i.float(2, "Entry 2 Drop from Entry 1 (%)", minval=0.01, step=0.1, group=g)
        g = "Exit Settings"
        self.use_tp = i.bool(True, "Enable Take Profit", group=g)
        self.tp_pct = i.float(3.0, "Take Profit (%)", minval=0.01, step=0.1, group=g)
        self.use_sl = i.bool(False, "Enable Stop Loss", group=g)
        self.sl_pct = i.float(8.0, "Stop Loss (%)", minval=0.01, step=0.1, group=g)
        self.rsi_exit = i.bool(True, "RSI Overbought Exit", group=g)
        self.entry1_fill = NA
        self.dca2_level = NA
        self.entry1_open = False
        self.entry2_open = False

    def on_bar(self):
        st = self.strategy
        close = self.close
        rsi_val = ta.rsi(self.rsi_src, self.rsi_len)
        rsi_oversold = ta.crossunder(rsi_val, self.oversold)
        rsi_obought = ta.crossover(rsi_val, self.overbought)
        ot_h = self.H("ot")
        ot_1 = ot_h[1]
        ot_h.set(st.opentrades)
        pos_size = st.position_size
        is_flat = pos_size == 0
        if is_flat:
            self.entry1_fill = NA
            self.dca2_level = NA
            self.entry1_open = False
            self.entry2_open = False
        if st.opentrades == 1 and ot_1 == 0 and not self.entry1_open:
            self.entry1_fill = st.opentrades_entry_price(0)
            self.dca2_level = self.entry1_fill * (1.0 - self.dca_pct / 100.0)
            self.entry1_open = True
        if st.opentrades == 2 and ot_1 == 1 and not self.entry2_open:
            self.entry2_open = True
        buy1_ok = rsi_oversold and close <= self.limit_price and is_flat
        buy2_ok = rsi_oversold and (not na(self.dca2_level)) and close <= self.dca2_level and self.entry1_open and not self.entry2_open
        if buy1_ok:
            st.entry("Buy1", st.long, comment="Entry 1")
        if buy2_ok:
            st.entry("Buy2", st.long, comment="Entry 2 DCA")
        if pos_size > 0:
            ep = st.position_avg_price
            tp_price = ep * (1.0 + self.tp_pct / 100.0) if self.use_tp else NA
            sl_price = ep * (1.0 - self.sl_pct / 100.0) if self.use_sl else NA
            st.exit("Exit1", from_entry="Buy1", limit=tp_price, stop=sl_price)
            st.exit("Exit2", from_entry="Buy2", limit=tp_price, stop=sl_price)
        if pos_size > 0 and self.rsi_exit and rsi_obought:
            st.close_all(comment="RSI OB Exit")

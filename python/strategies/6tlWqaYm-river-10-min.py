"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : river 10 min
Author       : lazyk42
Source URL   : https://www.tradingview.com/script/6tlWqaYm-river-10-min
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). A SuperTrend (3 x ATR10) flip enters (reversing), an ATR stop around the entry price is re-issued each bar while in a
position, a one-time break-even stop at the entry price is added once the close is 1.5% in profit, and a flip of a second, faster SuperTrend (1.5 x ATR7) closes the
position at the close.

Deviations from the original: none.
Not carried over: the channel plots and fill, the stop / break-even lines and labels (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, ta


class River10Min(Script):
    TITLE = "river 10 min"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=10, process_orders_on_close=True)
    SOURCE = {"id": "6tlWqaYm", "author": "lazyk42", "licence": "not stated",
              "url": "https://www.tradingview.com/script/6tlWqaYm-river-10-min"}

    def init(self):
        self.length = self.input.int(20, "Channel Length", group="Channel")
        self.mult = self.input.float(2.0, "Channel Multiplier", group="Channel")
        g = "Supertrend Entry"
        self.st_mult = self.input.float(3.0, "Trend Multiplier", group=g)
        self.st_len = self.input.int(10, "Trend Length", group=g)
        g = "Stop Loss"
        self.use_sl = self.input.bool(True, "הפעל סטופ לוס", group=g)
        self.sl_atr_len = self.input.int(14, "ATR Length", group=g)
        self.sl_atr_mult = self.input.float(2.0, "ATR מכפיל", group=g, step=0.1)
        g = "Breakeven"
        self.use_be = self.input.bool(True, "הפעל ברייקאיבן", group=g)
        self.be_trigger_pct = self.input.float(1.5, "% רווח להפעלת ברייקאיבן", group=g, step=0.1)
        g = "Early Exit"
        self.use_early_exit = self.input.bool(True, "הפעל יציאה מוקדמת", group=g)
        self.exit_mult = self.input.float(1.5, "מכפיל סופרטרנד יציאה", group=g, step=0.1)
        self.exit_len = self.input.int(7, "אורך סופרטרנד יציאה", group=g)
        self.be_active = False

    def on_bar(self):
        basis = ta.ema(self.close, self.length)
        dev = self.mult * ta.atr(10)
        self.plot(basis + dev, "upper", color=color.orange)
        self.plot(basis - dev, "lower", color=color.orange)
        supertrend, direction = ta.supertrend(self.st_mult, self.st_len)
        confirmed_direction = direction
        long_signal = ta.change(confirmed_direction) < 0
        short_signal = ta.change(confirmed_direction) > 0
        atr_val = ta.atr(self.sl_atr_len)
        st = self.strategy
        if st.position_size > 0 and self.use_sl:
            st.exit("SL Long", "Long", stop=st.opentrades_entry_price(0) - atr_val * self.sl_atr_mult)
        elif st.position_size < 0 and self.use_sl:
            st.exit("SL Short", "Short", stop=st.opentrades_entry_price(0) + atr_val * self.sl_atr_mult)
        if st.position_size > 0:
            entry_price = st.opentrades_entry_price(0)
            if (not self.be_active) and self.use_be:
                profit_pct = div(self.close - entry_price, entry_price) * 100
                if profit_pct >= self.be_trigger_pct:
                    st.exit("BE Long", "Long", stop=entry_price)
                    self.be_active = True
        if st.position_size < 0:
            entry_price = st.opentrades_entry_price(0)
            if (not self.be_active) and self.use_be:
                profit_pct = div(entry_price - self.close, entry_price) * 100
                if profit_pct >= self.be_trigger_pct:
                    st.exit("BE Short", "Short", stop=entry_price)
                    self.be_active = True
        if st.position_size == 0:
            self.be_active = False
        _, exit_direction = ta.supertrend(self.exit_mult, self.exit_len)
        confirmed_exit_dir = exit_direction
        exit_change = ta.change(confirmed_exit_dir)
        early_exit_long = self.use_early_exit and st.position_size > 0 and exit_change > 0
        early_exit_short = self.use_early_exit and st.position_size < 0 and exit_change < 0
        if early_exit_long:
            st.close("Long", comment="Early Exit")
        if early_exit_short:
            st.close("Short", comment="Early Exit")
        if long_signal:
            st.entry("Long", st.long)
        if short_signal:
            st.entry("Short", st.short)

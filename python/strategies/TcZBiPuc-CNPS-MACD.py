"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : CNPS MACD
Author       : Khanhtq26
Source URL   : https://www.tradingview.com/script/TcZBiPuc-CNPS-MACD
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. MACD(12,26,9) line crossing its signal enters long / short (reversing, 1 contract). While a
position is open at the bar close the stop (10 points) and optional target (30 points) are issued from
strategy.position_avg_price, so they first work on the bar after the fill. The strategy.close of the old side on the
opposite cross is queued after the reversing entry and finds no trade left to close.

Deviations from the original: none.
Not carried over: the SL / TP plots (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, ta


class CnpsMacd(Script):
    TITLE = "CNPS1-MACD"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="fixed", default_qty_value=1)
    SOURCE = {"id": "TcZBiPuc", "author": "Khanhtq26", "licence": "not stated",
              "url": "https://www.tradingview.com/script/TcZBiPuc-CNPS-MACD"}

    def init(self):
        self.use_tp = self.input.bool(True, "Sử dụng Chốt lời (TP)")
        self.trade_mode = self.input.string("Both", "Chế độ giao dịch", options=["Long Only", "Short Only", "Both"])
        self.sl_points = self.input.float(10, "Dừng lỗ (points)")
        self.tp_points = self.input.float(30, "Chốt lời (points)")

    def on_bar(self):
        macd_line, signal_line, hist = ta.macd(self.close, 12, 26, 9)
        long_cond = ta.crossover(macd_line, signal_line)
        close_long = ta.crossunder(macd_line, signal_line)
        short_cond = ta.crossunder(macd_line, signal_line)
        close_short = ta.crossover(macd_line, signal_line)
        st = self.strategy
        avg = st.position_avg_price
        long_sl = avg - self.sl_points
        long_tp = avg + self.tp_points
        short_sl = avg + self.sl_points
        short_tp = avg - self.tp_points
        if long_cond and (self.trade_mode == "Both" or self.trade_mode == "Long Only"):
            st.entry("Long", st.long)
        if short_cond and (self.trade_mode == "Both" or self.trade_mode == "Short Only"):
            st.entry("Short", st.short)
        if st.position_size > 0:
            st.exit("Exit Long", "Long", stop=long_sl, limit=long_tp if self.use_tp else NA)
            if close_long:
                st.close("Long")
        if st.position_size < 0:
            st.exit("Exit Short", "Short", stop=short_sl, limit=short_tp if self.use_tp else NA)
            if close_short:
                st.close("Short")

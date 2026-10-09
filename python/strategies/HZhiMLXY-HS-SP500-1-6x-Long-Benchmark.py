"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : HS SP500 1.6x Long Benchmark
Author       : HyperSignals
Source URL   : https://www.tradingview.com/script/HZhiMLXY-HS-SP500-1-6x-Long-Benchmark
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-09 by Claude (pine-to-python skill)

Buy-and-hold at 160 % of equity (margin_long 50 %) inside a date window; orders fill at the
signal bar's close (process_orders_on_close).

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script


class HsSp500Long(Script):
    TITLE = "HS SP500 1.6x Long Benchmark"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, pyramiding=0, default_qty_type="percent_of_equity",
                    default_qty_value=160, commission_type="percent", commission_value=0.075,
                    slippage=2, margin_long=50, margin_short=100, process_orders_on_close=True)
    SOURCE = {"id": "HZhiMLXY", "author": "HyperSignals", "licence": "not stated",
              "url": "https://www.tradingview.com/script/HZhiMLXY-HS-SP500-1-6x-Long-Benchmark"}

    def init(self):
        self.start_time = self.input.time(1521158400000, "Backtest start")
        self.end_time = self.input.time(1779753600000, "Backtest end")

    def on_bar(self):
        st = self.strategy
        in_window = self.time >= self.start_time and self.time <= self.end_time
        if in_window and st.position_size <= 0:
            st.entry("1.6x SP500 Long", st.long)
        if not in_window and st.position_size > 0:
            st.close("1.6x SP500 Long")

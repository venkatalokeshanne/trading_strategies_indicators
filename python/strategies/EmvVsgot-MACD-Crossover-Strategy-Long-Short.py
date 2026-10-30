"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : MACD Crossover Strategy [Long/Short]
Author       : Shiroi-
Source URL   : https://www.tradingview.com/script/EmvVsgot
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. MACD (12, 26, 9, EMA or SMA flavours) crossing its signal line (or the histogram crossing zero) goes long, the
opposite cross goes short; with a side disabled the signal only closes the opposite position. The strategy() call sits after the inputs in
the source; it has constant arguments so it maps to the class settings.

Deviations from the original: none.
Not carried over: histogram colouring, alertconditions, signal shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, ta


class MacdCrossover(Script):
    TITLE = "MACD Crossover Strategy [Long/Short]"
    PINE_VERSION = 6
    OVERLAY = False
    STRATEGY = dict(commission_type="percent", commission_value=0.1, slippage=2, default_qty_type="fixed", default_qty_value=1)
    SOURCE = {"id": "EmvVsgot", "author": "Shiroi-", "licence": "not stated",
              "url": "https://www.tradingview.com/script/EmvVsgot"}

    def init(self):
        g = "📊 MACD"
        self.source_input = self.input.source(self.close, "Source", group=g)
        self.fast_len = self.input.int(12, "Fast Length", minval=1, group=g)
        self.slow_len = self.input.int(26, "Slow Length", minval=1, group=g)
        self.sig_len = self.input.int(9, "Signal Length", minval=1, group=g)
        self.osc_type = self.input.string("EMA", "Oscillator MA Type", options=["EMA", "SMA"], group=g)
        self.sig_type = self.input.string("EMA", "Signal MA Type", options=["EMA", "SMA"], group=g)
        g2 = "⚙️ Strategy"
        self.entry_input = self.input.string("MACDxSignal", "Entry Condition", options=["MACDxSignal", "HistCross0"], group=g2)
        self.long_input = self.input.bool(True, "Enable Long", group=g2)
        self.short_input = self.input.bool(True, "Enable Short", group=g2)
        self.qty_input = self.input.float(1.0, "Lot Size", minval=0.01, step=0.01, group=g2)

    def ma(self, source, length, ma_type):
        if ma_type == "EMA":
            return ta.ema(source, length)
        if ma_type == "SMA":
            return ta.sma(source, length)
        return NA

    def on_bar(self):
        ma_fast = self.ma(self.source_input, self.fast_len, self.osc_type)
        ma_slow = self.ma(self.source_input, self.slow_len, self.osc_type)
        macd = ma_fast - ma_slow
        signal = self.ma(macd, self.sig_len, self.sig_type)
        hist = macd - signal
        if self.entry_input == "MACDxSignal":
            long_signal = ta.crossover(macd, signal)
            short_signal = ta.crossunder(macd, signal)
        else:
            long_signal = ta.crossover(hist, 0)
            short_signal = ta.crossunder(hist, 0)
        st = self.strategy
        if long_signal:
            if self.long_input:
                st.entry("Long", st.long, qty=self.qty_input)
            elif st.position_size < 0:
                st.close("Short")
        if short_signal:
            if self.short_input:
                st.entry("Short", st.short, qty=self.qty_input)
            elif st.position_size > 0:
                st.close("Long")
        self.plot(hist, "Histogram", color=color.green)
        self.plot(macd, "MACD", color=color.blue)
        self.plot(signal, "Signal Line", color=color.orange)

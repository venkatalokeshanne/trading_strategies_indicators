"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EMA Stack Strategy (EMA 1–6)
Author       : E_M_C_S
Source URL   : https://www.tradingview.com/script/DsnkjkXI-Configurable-EMA-Stack-Strategy
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Six EMAs (5/20/50/90/140/200) form a bias when the enabled ones are stacked in order; a fresh stack or a fast EMA1 / EMA2 cross inside a stacked market flips the
position at the bar close (process_orders_on_close). A cross back of EMA1 through EMA2 closes the trade unless the opposite entry fires on the same bar.

Deviations from the original: none.
Not carried over: the EMA plots (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class EmaStack(Script):
    TITLE = "EMA Stack Strategy (EMA 1–6)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, pyramiding=0, process_orders_on_close=True, commission_type="percent", commission_value=0.10, slippage=1)
    SOURCE = {"id": "DsnkjkXI", "author": "E_M_C_S", "licence": "not stated",
              "url": "https://www.tradingview.com/script/DsnkjkXI-Configurable-EMA-Stack-Strategy"}

    def init(self):
        self.show = [self.input.bool(True, f"Show EMA {k}") for k in range(1, 7)]
        self.use = [self.input.bool(True, f"Use EMA {k} In Bias") for k in range(1, 7)]
        defaults = [5, 20, 50, 90, 140, 200]
        self.lens = [self.input.int(defaults[k - 1], f"EMA {k} Length", minval=1, maxval=500) for k in range(1, 7)]
        self.prev_bull_bias = False
        self.prev_bear_bias = False

    def on_bar(self):
        ema1 = ta.ema(self.close, self.lens[0])
        ema2 = ta.ema(self.close, self.lens[1])
        ema3 = ta.ema(self.close, self.lens[2])
        ema4 = ta.ema(self.close, self.lens[3])
        ema5 = ta.ema(self.close, self.lens[4])
        ema6 = ta.ema(self.close, self.lens[5])
        emas = [ema1, ema2, ema3, ema4, ema5, ema6]
        bias_vals = [emas[k] for k in range(6) if self.use[k]]
        n = len(bias_vals)
        bull_bias = True
        bear_bias = True
        if n >= 2:
            for i in range(0, n - 1):
                bull_bias = bull_bias and (bias_vals[i] > bias_vals[i + 1])
                bear_bias = bear_bias and (bias_vals[i] < bias_vals[i + 1])
        new_bull_bias = bull_bias and not self.prev_bull_bias
        new_bear_bias = bear_bias and not self.prev_bear_bias
        self.prev_bull_bias, self.prev_bear_bias = bool(bull_bias), bool(bear_bias)
        fast_bull_ok = (ema1 > ema2) if (self.use[0] and self.use[1]) else True
        fast_bear_ok = (ema1 < ema2) if (self.use[0] and self.use[1]) else True
        full_bull = bull_bias and fast_bull_ok
        full_bear = bear_bias and fast_bear_ok
        cross_up = ta.crossover(ema1, ema2)
        cross_dn = ta.crossunder(ema1, ema2)
        long_signal = full_bull and (cross_up or new_bull_bias)
        short_signal = full_bear and (cross_dn or new_bear_bias)
        st = self.strategy
        exit_long_signal = st.position_size > 0 and cross_dn
        exit_short_signal = st.position_size < 0 and cross_up
        if long_signal and st.position_size <= 0:
            st.close("Short", comment="Close Short")
            st.entry("Long", st.long, comment="Long Entry")
        if short_signal and st.position_size >= 0:
            st.close("Long", comment="Close Long")
            st.entry("Short", st.short, comment="Short Entry")
        if exit_long_signal and not short_signal:
            st.close("Long", comment="Long Exit")
        if exit_short_signal and not long_signal:
            st.close("Short", comment="Short Exit")
        self.plot(ema1, "EMA 1", color=color.blue, linewidth=2)
        self.plot(ema2, "EMA 2", color=color.green, linewidth=2)
        self.plot(ema3, "EMA 3", color=color.red, linewidth=2)

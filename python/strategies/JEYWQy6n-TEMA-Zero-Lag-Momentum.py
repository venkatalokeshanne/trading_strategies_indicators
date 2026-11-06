"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : TEMA Zero-Lag Momentum
Author       : egoigor1976
Source URL   : https://www.tradingview.com/script/JEYWQy6n-TEMA-Zero-Lag-Momentum
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. `avg` is the triple EMA (3*(ema1-ema2)+ema3); its history goes through S().
On a signal the opposite trade is closed (only if it is open when the script runs) and the new one entered.

Deviations from the original: none.
Not carried over: the alert() texts (alerts do not affect a backtest).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color, ta


class TemaZeroLagMomentum(Script):
    TITLE = "TEMA Zero-Lag Momentum"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="cash", default_qty_value=1000, pyramiding=1,
                    commission_type="percent", commission_value=0.05)
    SOURCE = {"id": "JEYWQy6n", "author": "egoigor1976", "licence": "not stated",
              "url": "https://www.tradingview.com/script/JEYWQy6n-TEMA-Zero-Lag-Momentum"}

    def init(self):
        self.len = self.input.int(81, "TEMA period")
        self.f_fast_length = self.input.int(29, "Filter fast length")
        self.f_slow_length = self.input.int(27, "Filter slow length")
        self.f_signal_length = self.input.int(5, "Filter signal length")

    def on_bar(self):
        real_c = self.close
        ema1 = ta.ema(real_c, self.len)
        ema2 = ta.ema(ema1, self.len)
        ema3 = ta.ema(ema2, self.len)
        avg_now = 3 * (ema1 - ema2) + ema3
        avg_prev = S(avg_now)[1]
        f_source = self.close
        f_fast_ma = ta.ema(f_source, self.f_fast_length)
        f_slow_ma = ta.ema(f_source, self.f_slow_length)
        f_macd = f_fast_ma - f_slow_ma
        f_signal = ta.sma(f_macd, self.f_signal_length)
        cross_up = ta.crossover(f_macd, f_signal)
        cross_dn = ta.crossunder(f_macd, f_signal)
        long_signal = cross_up and avg_now > avg_prev
        short_signal = cross_dn and avg_now < avg_prev
        st = self.strategy
        if long_signal:
            st.close("Short", comment="Close Short")
            st.entry("Long", st.long, comment="Open Long")
            self.alert("Buy Signal: TEMA Zero-Lag Momentum")
        if short_signal:
            st.close("Long", comment="Close Long")
            st.entry("Short", st.short, comment="Open Short")
            self.alert("Sell Signal: TEMA Zero-Lag Momentum")
        self.plot(avg_now, title="TEMA Line", color=color.new(color.blue, 0), linewidth=2)

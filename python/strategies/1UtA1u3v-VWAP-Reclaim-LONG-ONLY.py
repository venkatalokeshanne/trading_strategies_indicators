"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : VWAP Squeeze Reclaim (LONG ONLY)
Author       : omkarg007
Source URL   : https://www.tradingview.com/script/1UtA1u3v-VWAP-Reclaim-LONG-ONLY
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Long (flat only) when the Supertrend(1.5, 21) is up, the close is above the session VWAP,
MACD(12,26,9) is above its signal and above zero, RSI(14) < 60, +DI > -DI and it is before 15:00 exchange time; the
position is closed (next open) when the close is under VWAP, MACD falls under its signal or the Supertrend turns down.
The squeeze, crosses and end-of-day constants of the original feed no order and are kept only where they are cheap.

Deviations from the original: none.
Not carried over: the plots, BUY / EXIT shapes and alert() calls (no effect on orders).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, ta


class VwapSqueezeReclaim(Script):
    TITLE = "VWAP Squeeze Reclaim (LONG ONLY)"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "1UtA1u3v", "author": "omkarg007", "licence": "not stated",
              "url": "https://www.tradingview.com/script/1UtA1u3v-VWAP-Reclaim-LONG-ONLY"}

    def init(self):
        self.bb_length = self.input.int(20, "BB Length")
        self.bb_mult = self.input.float(2.0, "BB Multiplier")
        self.rsi_length = self.input.int(14, "RSI Length")

    def on_bar(self):
        vwap_value = ta.vwap(self.close)
        basis = ta.sma(self.close, self.bb_length)
        dev = self.bb_mult * ta.stdev(self.close, self.bb_length)
        upper = basis + dev
        lower = basis - dev
        bb_width = div(upper - lower, basis)
        is_squeeze = bb_width < 0.05
        recent_squeeze = ta.barssince(is_squeeze) < 20
        macd_line, signal_line, _ = ta.macd(self.close, 12, 26, 9)
        macd_bull = macd_line > signal_line
        rsi = ta.rsi(self.close, self.rsi_length)
        diplus, diminus, adx = ta.dmi(14, 14)
        dmi_bull = diplus > diminus
        supertrend, direction = ta.supertrend(1.5, 21)
        supertrend_bull = direction < 0
        above_vwap = self.close > vwap_value
        below_vwap = self.close < vwap_value
        vwap_cross_up = ta.crossover(self.close, vwap_value)
        vwap_cross_down = ta.crossunder(self.close, vwap_value)
        hour, minute = self.hour(), self.minute()
        no_new_entries = (hour > 15) or (hour == 15 and minute >= 0)
        buy_signal = (direction < 0 and above_vwap and macd_bull and (not no_new_entries) and macd_line > 0
                      and rsi < 60 and dmi_bull and supertrend_bull)
        sell_signal = vwap_cross_down or below_vwap or macd_line < signal_line or direction > 0
        st = self.strategy
        if buy_signal and st.position_size == 0:
            st.entry("Long", st.long)
        if sell_signal and st.position_size > 0:
            st.close("Long")
        self.plot(supertrend, title="Supertrend", color=color.green if supertrend_bull else color.red, linewidth=2)
        self.plot(vwap_value, title="VWAP", color=color.blue)

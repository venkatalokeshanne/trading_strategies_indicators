"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Rudy Range Regime v2
Author       : bigboo407
Source URL   : https://www.tradingview.com/script/kJ3E1iWN-Rudy-Range-Regime-v2
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A "flat" regime (ADX(14) < 25, RSI(14) between 35 and 65, Bollinger(20, 2) width under 8 % of the
basis) buys one unit when flat. holdCount counts the bars a position has been open at the close (the script reads the position
before that bar's fill); the position is closed (next open) after 21 bars or when the close is more than 5 % under the
signal-bar close.

Deviations from the original: none.
Not carried over: the historical-volatility proxy, plots, background, shapes and the dashboard table (cosmetic; the proxy
feeds no order).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, ta


class RudyRangeRegime(Script):
    TITLE = "Rudy Range Regime v2"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=1, initial_capital=10000,
                    commission_type="percent", commission_value=0.1)
    SOURCE = {"id": "kJ3E1iWN", "author": "bigboo407", "licence": "not stated",
              "url": "https://www.tradingview.com/script/kJ3E1iWN-Rudy-Range-Regime-v2"}

    def init(self):
        self.p_adx = self.input.int(14, "ADX Lookback")
        self.p_adx_lim = self.input.int(25, "ADX Ceiling")
        self.p_rsi = self.input.int(14, "RSI Lookback")
        self.p_rsi_lo = self.input.int(35, "RSI Floor")
        self.p_rsi_hi = self.input.int(65, "RSI Ceiling")
        self.p_bb = self.input.int(20, "BB Lookback")
        self.p_bb_lim = self.input.float(8.0, "BB Width Ceiling Pct")
        self.p_hold = self.input.int(21, "Hold Duration Bars")
        self.hold_count = 0
        self.basis_price = 0.0

    def on_bar(self):
        dp_i, dm_i, adx_v = ta.dmi(self.p_adx, self.p_adx)
        rsi_v = ta.rsi(self.close, self.p_rsi)
        b_mid, b_up, b_lo = ta.bb(self.close, self.p_bb, 2)
        b_width = div(b_up - b_lo, b_mid) * 100
        is_flat = adx_v < self.p_adx_lim and rsi_v > self.p_rsi_lo and rsi_v < self.p_rsi_hi and b_width < self.p_bb_lim
        st = self.strategy
        if is_flat and st.position_size == 0:
            st.entry("RR_Sell", st.long)
            self.hold_count = 0
            self.basis_price = float(self.close)
        if st.position_size > 0:
            self.hold_count += 1
            drawdown = div(self.close - self.basis_price, self.basis_price) * 100
            if self.hold_count >= self.p_hold:
                st.close("RR_Sell", comment="Duration Exit")
                self.hold_count = 0
            if drawdown < -5.0:
                st.close("RR_Sell", comment="Protective Exit")
                self.hold_count = 0
        self.plot(b_up, "BB Upper", color=color.gray)
        self.plot(b_lo, "BB Lower", color=color.gray)
        self.plot(adx_v, "ADX", color=color.purple)

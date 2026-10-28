"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Supertrend+atr
Author       : Darkphi
Source URL   : https://www.tradingview.com/script/bK7ooPvS
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A hand-written Supertrend (ATR(10) x 3 around hl2, trend flips when the close crosses the
previous bar's band) turns long/short on a flip; a flip is only traded when the ATR is not in "consolidation" (ATR(10)
below 0.5 x SMA20 of ATR(14)). The flip closes the opposite id and enters with risk-based size (5 % of equity over three ATRs,
x4 leverage); a trailing exit with trail_points = trail_offset = 1.5 ATR (read as ticks, as in the original) is issued with
the entry on the signal bar.

Deviations from the original: none.
Not carried over: the trend-line plots and BUY / SELL shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, nz, pmath, ta


class SupertrendAtr(Script):
    TITLE = "Supertrend+atr"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000, default_qty_type="cash", commission_type="percent", commission_value=0.05)
    SOURCE = {"id": "bK7ooPvS", "author": "Darkphi", "licence": "not stated",
              "url": "https://www.tradingview.com/script/bK7ooPvS"}

    def init(self):
        self.periods = self.input.int(10, "ATR Period")
        self.multiplier = self.input.float(3.0, "ATR Multiplier", step=0.1)
        self.change_atr = self.input.bool(True, "Use built-in ATR?")
        self.risk_perc = self.input.float(5.0, "Risk per trade (%)", step=0.1)
        self.leverage = self.input.float(4.0, "Leverage", step=0.1)
        self.trail_mult = self.input.float(1.5, "Trailing Stop ATR Mult", step=0.1)
        self.atr_length = self.input.int(14, "ATR Length pour Filtre")
        self.atr_mult = self.input.float(0.5, "ATR Multiplier pour Filtre")
        self.sma_atr_length = self.input.int(20, "SMA ATR Length")
        self.up_prev = NA
        self.dn_prev = NA
        self.trend_prev = NA

    def on_bar(self):
        atr_a = ta.atr(self.periods)
        atr_b = ta.atr(self.atr_length)
        atr_filter = atr_a < ta.sma(atr_b, self.sma_atr_length) * self.atr_mult
        atr_custom = ta.sma(ta.tr(False), self.periods)
        atr_val = ta.atr(self.periods) if self.change_atr else atr_custom
        src = self.hl2
        up = src - (self.multiplier * atr_val)
        up1 = nz(self.up_prev, up)
        up = pmath.max(up, up1) if self.close[1] > up1 else up
        dn = src + (self.multiplier * atr_val)
        dn1 = nz(self.dn_prev, dn)
        dn = pmath.min(dn, dn1) if self.close[1] < dn1 else dn
        trend = nz(self.trend_prev, 1)
        trend = 1 if (trend == -1 and self.close > dn1) else (-1 if (trend == 1 and self.close < up1) else trend)
        buy_signal = trend == 1 and nz(self.trend_prev, 0) == -1
        sell_signal = trend == -1 and nz(self.trend_prev, 0) == 1
        self.up_prev, self.dn_prev, self.trend_prev = up, dn, trend
        st = self.strategy
        capital = st.equity
        risk_amount = capital * (self.risk_perc / 100)
        stop_dist = pmath.max(atr_val * self.multiplier, self.syminfo.mintick)
        raw_size = div(risk_amount, stop_dist)
        leveraged_size = raw_size * self.leverage
        pos_size = pmath.max(0.0, leveraged_size)
        pos_size = pmath.min(pos_size, 1e9)
        can_trade = pos_size > 0 and not (pos_size != pos_size) and not atr_filter
        trail_offset = atr_val * self.trail_mult
        if buy_signal and can_trade:
            st.close("Short")
            st.entry("Long", st.long, qty=pos_size)
            st.exit("Long Exit", from_entry="Long", trail_offset=trail_offset, trail_points=trail_offset)
        if sell_signal and can_trade:
            st.close("Long")
            st.entry("Short", st.short, qty=pos_size)
            st.exit("Short Exit", from_entry="Short", trail_offset=trail_offset, trail_points=trail_offset)
        self.plot(up if trend == 1 else NA, "Up Trend", color=color.green, linewidth=2)
        self.plot(dn if trend == -1 else NA, "Down Trend", color=color.red, linewidth=2)

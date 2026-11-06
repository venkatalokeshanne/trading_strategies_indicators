"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : BB + MACD v6.1.5 (Qing Smart Distribution)
Author       : Z8830
Source URL   : https://www.tradingview.com/script/qo43NaGV-BB-MACD-v6-1-5-Qing-Smart-Distribution
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A close crossing up through the Bollinger basis with solid MACD momentum (or a MACD signal cross-up above the basis with a positive
histogram) on a bullish, average-volume bar goes long. Exits: distribution (near the upper band, two falling histogram bars, stalling bearish bar), trend end
(below basis minus an ATR buffer on a bearish bar) or blow-off (above the upper band with MACD far above its signal) close the long at the next open.

Deviations from the original: none.
Not carried over: band plots, fill and signal shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color, ta


class BbMacdQing(Script):
    TITLE = "Qing BB + MACD v6.1.5 (Smart Distribution)"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100,
                    commission_type="percent", commission_value=0.1)
    SOURCE = {"id": "qo43NaGV", "author": "Z8830", "licence": "not stated",
              "url": "https://www.tradingview.com/script/qo43NaGV-BB-MACD-v6-1-5-Qing-Smart-Distribution"}

    def init(self):
        self.bb_length = self.input.int(20, "BB Length", group="Bollinger Bands")
        self.bb_mult = self.input.float(2.0, "BB Multiplier", group="Bollinger Bands")
        self.fast_len = self.input.int(6, "MACD Fast Length", group="MACD")
        self.slow_len = self.input.int(12, "MACD Slow Length", group="MACD")
        self.sig_len = self.input.int(8, "MACD Signal Length", group="MACD")
        self.atr_mult = self.input.float(0.5, "Exit ATR Buffer (Trend End)", group="Filters")
        self.use_vol = self.input.bool(True, "Require Volume Confirmation", group="Filters")

    def on_bar(self):
        basis = ta.sma(self.close, self.bb_length)
        dev = self.bb_mult * ta.stdev(self.close, self.bb_length)
        upper = S(basis + dev)
        macd_line, signal_line, hist = ta.macd(self.close, self.fast_len, self.slow_len, self.sig_len)
        hist = S(hist)
        atr = ta.atr(14)
        avg_vol = ta.sma(self.volume, 20)
        vol_ok = (self.volume >= avg_vol) if self.use_vol else True
        close = S(self.close)
        is_solid_momentum = (macd_line > signal_line) and (hist[0] > 0) and (hist[0] > hist[1])
        price_breakout = ta.crossover(self.close, basis) and is_solid_momentum
        macd_breakout = ta.crossover(macd_line, signal_line) and (self.close > basis) and (hist[0] > 0)
        entry_signal = (price_breakout or macd_breakout) and vol_ok and (self.close > self.open)
        near_upper_bb = ta.highest(self.high, 3) >= upper[1]
        macd_bleeding = (hist[0] < hist[1]) and (hist[1] < hist[2])
        price_stalling = (self.close < self.open) and (close[0] <= close[1])
        exit_distribution = near_upper_bb and macd_bleeding and price_stalling
        exit_trend_end = (self.close < (basis - (atr * self.atr_mult))) and (self.close < self.open)
        exit_exhaustion = (self.close > upper[0]) and (macd_line > 0) and (macd_line > (signal_line * 2.5))
        st = self.strategy
        if entry_signal:
            st.entry("Long", st.long)
        if exit_distribution or exit_trend_end or exit_exhaustion:
            st.close("Long", comment="Distribution Exit" if exit_distribution else ("Blow-off Exit" if exit_exhaustion else "Trend End Exit"))
        self.plot(basis, "Basis", color=color.white, linewidth=2)
        self.plot(upper[0], "Upper", color=color.red)

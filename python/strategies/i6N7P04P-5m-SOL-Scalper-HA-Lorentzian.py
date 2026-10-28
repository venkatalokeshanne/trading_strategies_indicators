"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : 5m SOL Scalper: HA + Lorentzian
Author       : BipinBihariPatra
Source URL   : https://www.tradingview.com/script/i6N7P04P-5m-SOL-Scalper-HA-Lorentzian
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The smoothed Heikin-Ashi candle uses EMA(8) of each price; haOpen starts from
(sOpen + sClose) / 2 while its history is na and then averages the previous haOpen and haClose. The
"Lorentzian velocity" is a linear-regression end value of the 14-bar price change. The bracket is
placed with the entry (works from the fill bar).

Deviations from the original: none.
Not carried over: the plotcandle() drawing of the smoothed candles (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, na, ta


class SolScalperHaLorentzian(Script):
    TITLE = "5m SOL Scalper: HA + Lorentzian"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000, default_qty_type="percent_of_equity", default_qty_value=20)
    SOURCE = {"id": "i6N7P04P", "author": "BipinBihariPatra", "licence": "not stated",
              "url": "https://www.tradingview.com/script/i6N7P04P-5m-SOL-Scalper-HA-Lorentzian"}

    def init(self):
        self.ha_len = self.input.int(8, "HA Smoothing (Shortened for 5m)")
        self.lor_window = self.input.int(14, "Lorentzian Lookback (Faster)")
        self.tp_percent = self.input.float(1.5, "Take Profit %") / 100
        self.sl_percent = self.input.float(0.8, "Stop Loss %") / 100

    def on_bar(self):
        s_open = ta.ema(self.open, self.ha_len)
        s_high = ta.ema(self.high, self.ha_len)
        s_low = ta.ema(self.low, self.ha_len)
        s_close = ta.ema(self.close, self.ha_len)
        ha_close = (s_open + s_high + s_low + s_close) / 4
        prev_ha_open = self.H("ha_open")[1]
        prev_ha_close = self.H("ha_close")[1]
        ha_open = (s_open + s_close) / 2 if na(prev_ha_open) else (prev_ha_open + prev_ha_close) / 2
        self.H("ha_open").set(ha_open)
        self.H("ha_close").set(ha_close)
        lorentz_velocity = ta.linreg(self.close - self.close[self.lor_window], self.lor_window, 0)
        lorentz_bullish = lorentz_velocity > 0
        lorentz_bearish = lorentz_velocity < 0
        cross_up = ta.crossover(ha_close, ha_open)
        cross_dn = ta.crossunder(ha_close, ha_open)
        long_condition = cross_up and lorentz_bullish
        short_condition = cross_dn and lorentz_bearish
        st = self.strategy
        if long_condition:
            st.entry("Long", st.long)
            st.exit("Exit Long", "Long", limit=self.close * (1 + self.tp_percent), stop=self.close * (1 - self.sl_percent))
        if short_condition:
            st.entry("Short", st.short)
            st.exit("Exit Short", "Short", limit=self.close * (1 - self.tp_percent), stop=self.close * (1 + self.sl_percent))
        self.plotshape(long_condition, title="BUY")
        self.plotshape(short_condition, title="SELL")

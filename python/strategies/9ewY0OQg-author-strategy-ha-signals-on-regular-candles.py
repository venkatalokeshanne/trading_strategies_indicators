"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Author Strategy - HA signals on regular candles
Author       : AssekeTradeLab
Source URL   : https://www.tradingview.com/script/9ewY0OQg-author-strategy-ha-signals-on-regular-candles
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Heikin-Ashi candles (computed here from the chart candles: close = ohlc4, open = average of the previous HA open and close seeded with (open + close) / 2,
high / low include the HA open and close, which is what request.security on ticker.heikinashi returns on the same timeframe) drive a Chandelier-style ATR trailing-stop flip; a flip
in the direction of the ZLSMMA (zero-lag smoothed MA of HA closes) enters at the next open, with the signal bar's low / high as a stop issued once the position exists. A HA close back through
the ZLSMMA exits.

Deviations from the original: the ticker.heikinashi security calls are computed in place.
Not carried over: the ZLSMMA plot and the Buy / Sell labels.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, color, div, na, nz, pmath, ta


class HaOnRegular(Script):
    TITLE = "Author Strategy - HA signals on regular candles"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, initial_capital=10000, commission_type="percent", commission_value=0.04)
    SOURCE = {"id": "9ewY0OQg", "author": "AssekeTradeLab", "licence": "not stated",
              "url": "https://www.tradingview.com/script/9ewY0OQg-author-strategy-ha-signals-on-regular-candles"}

    def init(self):
        self.atr_period = self.input.int(1, "Chandelier ATR Period", minval=1)
        self.atr_multiplier = self.input.float(2.0, "Chandelier ATR Multiplier", step=0.1)
        self.smma_length = self.input.int(50, "ZLSMA Length", minval=1)
        self.show_labels = self.input.bool(True, "Show Buy/Sell Labels")
        self.show_zlsmma = self.input.bool(True, "Show ZL SMMA")
        self.ha_open_prev = NA
        self.ha_close_prev = NA
        self.smma_value = NA
        self.long_stop_ha = NA
        self.short_stop_ha = NA
        self.dir = 1
        self.dir_prev = NA
        self.long_sl = NA
        self.short_sl = NA

    def on_bar(self):
        ha_close_v = (self.open + self.high + self.low + self.close) / 4
        ha_open_v = (self.open + self.close) / 2 if na(self.ha_open_prev) else (self.ha_open_prev + self.ha_close_prev) / 2
        ha_high_v = pmath.max(self.high, ha_open_v, ha_close_v)
        ha_low_v = pmath.min(self.low, ha_open_v, ha_close_v)
        self.ha_open_prev, self.ha_close_prev = ha_open_v, ha_close_v
        ha_close = S(ha_close_v)
        lag = pmath.max(1, int(pmath.floor(self.smma_length / 2)))
        zl_source = ha_close[0] + (ha_close[0] - ha_close[lag])
        sma_part = ta.sma(zl_source, self.smma_length)
        self.smma_value = sma_part if na(self.smma_value) else div(self.smma_value * (self.smma_length - 1) + zl_source, self.smma_length)
        zl_smma = self.smma_value
        atr_ha = ta.atr(self.atr_period)
        long_stop_raw = ta.highest(ha_high_v, self.atr_period) - atr_ha * self.atr_multiplier
        short_stop_raw = ta.lowest(ha_low_v, self.atr_period) + atr_ha * self.atr_multiplier
        ls1 = nz(self.long_stop_ha, long_stop_raw)
        ss1 = nz(self.short_stop_ha, short_stop_raw)
        hc1 = ha_close[1]
        long_stop_ha = pmath.max(long_stop_raw, ls1) if hc1 > ls1 else long_stop_raw
        short_stop_ha = pmath.min(short_stop_raw, ss1) if hc1 < ss1 else short_stop_raw
        ss1b = nz(self.short_stop_ha, short_stop_ha)
        ls1b = nz(self.long_stop_ha, long_stop_ha)
        if ha_close[0] > ss1b:
            new_dir = 1
        elif ha_close[0] < ls1b:
            new_dir = -1
        else:
            new_dir = nz(self.dir, 1)
        dir_prev = self.dir
        self.long_stop_ha, self.short_stop_ha, self.dir = long_stop_ha, short_stop_ha, new_dir
        buy_signal = new_dir == 1 and dir_prev == -1
        sell_signal = new_dir == -1 and dir_prev == 1
        long_condition = buy_signal and ha_close[0] > zl_smma
        short_condition = sell_signal and ha_close[0] < zl_smma
        st = self.strategy
        if long_condition and st.position_size <= 0:
            self.long_sl = float(self.low)
            st.entry("Long", st.long)
        if short_condition and st.position_size >= 0:
            self.short_sl = float(self.high)
            st.entry("Short", st.short)
        if st.position_size > 0 and not na(self.long_sl):
            st.exit("Long SL", "Long", stop=self.long_sl)
        if st.position_size < 0 and not na(self.short_sl):
            st.exit("Short SL", "Short", stop=self.short_sl)
        exit_long = st.position_size > 0 and ha_close[0] < zl_smma
        exit_short = st.position_size < 0 and ha_close[0] > zl_smma
        if exit_long:
            st.close("Long", comment="MA Exit")
        if exit_short:
            st.close("Short", comment="MA Exit")
        if st.position_size == 0:
            self.long_sl = NA
            self.short_sl = NA
        self.plot(zl_smma if self.show_zlsmma else NA, "ZL SMMA", color=color.white, linewidth=2)

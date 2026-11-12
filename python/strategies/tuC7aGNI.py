"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Strategy 432 BTC - Donchian Breakout Continuation
Author       : Fran_Pineda
Source URL   : https://www.tradingview.com/script/tuC7aGNI
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close: orders fill at the signal bar's close). A close above the previous 30-bar Donchian high (below the low for the optional shorts) by at least a fraction of the ATR, with ADX above the minimum and the close on the right side of the 200 EMA, enters while flat. The position exits when the close falls back through the opposite Donchian
extreme or after the maximum number of bars in the position.
Deviations from the original: none.
Not carried over: the signal markers and Donchian / EMA plots (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, ta


class DonchianBreakout432(Script):
    TITLE = "Strategy 432 BTC - Donchian Breakout Continuation"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=95, pyramiding=0, commission_type="percent",
                    commission_value=0.1, process_orders_on_close=True)
    SOURCE = {"id": "tuC7aGNI", "author": "Fran_Pineda", "licence": "not stated", "url": "https://www.tradingview.com/script/tuC7aGNI"}

    def init(self):
        i = self.input
        self.dc_len = i.int(30, "Donchian Length", minval=1)
        self.atr_len = i.int(14, "ATR Length", minval=1)
        self.adx_len = i.int(14, "ADX Length", minval=1)
        self.ema200_len = i.int(200, "EMA 200 Length", minval=1)
        self.min_break_atr = i.float(0.5, "Min Breakout ATR", step=0.1)
        self.adx_min = i.float(22.0, "ADX mínimo", step=0.5)
        self.hold_bars = i.int(20, "Máximo de barras en posición", minval=1)
        self.allow_shorts = i.bool(False, "Permitir shorts")
        self.entry_bar_index = NA

    def on_bar(self):
        st = self.strategy
        close = self.close
        dc_high = ta.highest(self.high[1], self.dc_len)
        dc_low = ta.lowest(self.low[1], self.dc_len)
        atr_value = ta.atr(self.atr_len)
        ema200 = ta.ema(close, self.ema200_len)
        plus_di, minus_di, adx_value = ta.dmi(self.adx_len, self.adx_len)
        long_breakout_mag = div(close - dc_high, atr_value) if (close > dc_high and atr_value > 0) else 0.0
        short_breakout_mag = div(dc_low - close, atr_value) if (close < dc_low and atr_value > 0) else 0.0
        in_long = st.position_size > 0
        in_short = st.position_size < 0
        flat = st.position_size == 0
        bars_held = (self.bar_index - self.entry_bar_index) if not na(self.entry_bar_index) else NA
        indicators_ready = (not na(dc_high)) and (not na(dc_low)) and (not na(atr_value)) and (not na(adx_value)) and (not na(ema200))
        long_entry = indicators_ready and flat and close > dc_high and adx_value >= self.adx_min and close > ema200 and long_breakout_mag >= self.min_break_atr
        short_entry = indicators_ready and self.allow_shorts and flat and close < dc_low and adx_value >= self.adx_min and close < ema200 and short_breakout_mag >= self.min_break_atr
        long_exit = in_long and (close < dc_low or ((not na(bars_held)) and bars_held >= self.hold_bars))
        short_exit = in_short and (close > dc_high or ((not na(bars_held)) and bars_held >= self.hold_bars))
        if long_entry:
            st.entry("Long", st.long, alert_message="ENTRY_LONG")
            self.entry_bar_index = self.bar_index
        if short_entry:
            st.entry("Short", st.short, alert_message="ENTRY_SHORT")
            self.entry_bar_index = self.bar_index
        if long_exit:
            st.close("Long", alert_message="EXIT_LONG")
            self.entry_bar_index = NA
        if short_exit:
            st.close("Short", alert_message="EXIT_SHORT")
            self.entry_bar_index = NA

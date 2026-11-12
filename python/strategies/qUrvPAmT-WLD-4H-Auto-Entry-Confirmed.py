"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : WLD 4H Auto Entry Confirmed
Author       : farshad_hamidi1011
Source URL   : https://www.tradingview.com/script/qUrvPAmT-WLD-4H-Auto-Entry-Confirmed
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A UT-Bot ATR trailing stop (ATR period 1, factor 2) gives buy / sell signals when the price crosses
it; a signal is accepted only when MACD is on the same side of its signal line and both the close and the low (high) are beyond
EMA50, and only if no signal was accepted within the last `maxBarsHold` bars. The accepted bar enters on that bar's close
(filled at the next open). An open position is closed (next open) after `maxBarsHold` bars since its entry, or when the opposite
signal is confirmed; closing resets the signal state.

Deviations from the original: none.
Not carried over: the BUY / SELL label shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, pmath, ta


class WldAutoEntry(Script):
    TITLE = "WLD 4H Auto Entry Confirmed"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "qUrvPAmT", "author": "farshad_hamidi1011", "licence": "not stated",
              "url": "https://www.tradingview.com/script/qUrvPAmT-WLD-4H-Auto-Entry-Confirmed"}

    def init(self):
        self.a = self.input.float(2.0, title="UT Bot Key Value")
        self.c = self.input.int(1, title="UT Bot ATR Period")
        self.ema_length = self.input.int(50, title="EMA Length")
        self.max_bars_hold = self.input.int(4, title="Max Bars to Hold")
        self.x_atr_trailing_stop = NA
        self.signal_bar = NA
        self.signal_type = "none"

    def on_bar(self):
        ema50 = ta.ema(self.close, self.ema_length)
        macd_line, signal_line, _ = ta.macd(self.close, 12, 26, 9)
        x_atr = ta.atr(self.c)
        n_loss = self.a * x_atr
        src = self.close
        prev = self.x_atr_trailing_stop
        if na(prev):
            stop = src - n_loss
        elif src > prev and src[1] > prev:
            stop = pmath.max(prev, src - n_loss)
        elif src < prev and src[1] < prev:
            stop = pmath.min(prev, src + n_loss)
        elif src > prev:
            stop = src - n_loss
        else:
            stop = src + n_loss
        self.x_atr_trailing_stop = stop
        ema1 = ta.ema(src, 1)
        above = ta.crossover(ema1, stop)
        below = ta.crossover(stop, ema1)
        buy_signal = src > stop and above
        sell_signal = src < stop and below
        if na(self.signal_bar) or (self.bar_index > self.signal_bar + self.max_bars_hold):
            if buy_signal and macd_line > signal_line and self.close > ema50 and self.low > ema50:
                self.signal_bar = self.bar_index
                self.signal_type = "long"
            elif sell_signal and macd_line < signal_line and self.close < ema50 and self.high < ema50:
                self.signal_bar = self.bar_index
                self.signal_type = "short"
        enter_long = self.signal_type == "long" and self.bar_index == self.signal_bar and self.close > ema50 and macd_line > signal_line
        enter_short = self.signal_type == "short" and self.bar_index == self.signal_bar and self.close < ema50 and macd_line < signal_line
        st = self.strategy
        if enter_long:
            st.entry("Long", st.long)
        if enter_short:
            st.entry("Short", st.short)
        in_position = st.opentrades > 0
        bars_since_entry = self.bar_index - st.opentrades_entry_bar_index(0) if in_position else NA
        exit_trade = False
        if in_position and bars_since_entry >= self.max_bars_hold:
            exit_trade = True
        opposite_confirmed = False
        if self.signal_type == "long":
            opposite_confirmed = sell_signal and self.close < ema50 and macd_line < signal_line
        elif self.signal_type == "short":
            opposite_confirmed = buy_signal and self.close > ema50 and macd_line > signal_line
        if in_position and opposite_confirmed:
            exit_trade = True
        if exit_trade:
            st.close_all()
            self.signal_bar = NA
            self.signal_type = "none"

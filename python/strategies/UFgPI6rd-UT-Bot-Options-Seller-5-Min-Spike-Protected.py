"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : UT Bot Options Seller (5-Min Spike Protected)
Author       : gowdaprabhu4
Source URL   : https://www.tradingview.com/script/UFgPI6rd-UT-Bot-Options-Seller-5-Min-Spike-Protected
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The trade window is the Indian cash session "0915-1500" in Asia/Kolkata on every
day of the week ("1234567"); outside it every position is closed at the next open. `time(...)` returns na
outside the window, which Pine treats as false in `if inTradeWindow` and as true in `not inTradeWindow`.
The trailing stop is a var series read through H() (`xATRTrailingStop[1]`).

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, na, nz, pmath, ta


class UtBotOptionsSeller(Script):
    TITLE = "UT Bot Options Seller (5-Min Spike Protected)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "UFgPI6rd", "author": "gowdaprabhu4", "licence": "not stated",
              "url": "https://www.tradingview.com/script/UFgPI6rd-UT-Bot-Options-Seller-5-Min-Spike-Protected"}

    def init(self):
        self.ut_key = self.input.float(2.0, "UT Bot Key Value")
        self.ut_atr_period = self.input.int(10, "UT Bot ATR Period")
        self.rsi_period = self.input.int(14, "RSI Period")
        self.rsi_pe_min = self.input.int(3, "PE Sell Min RSI")
        self.rsi_pe_max = self.input.int(60, "PE Sell Max RSI")
        self.rsi_ce_min = self.input.int(40, "CE Sell Min RSI")
        self.rsi_ce_max = self.input.int(100, "CE Sell Max RSI")
        self.adx_period = self.input.int(14, "ADX Period")
        self.adx_threshold = self.input.float(20.0, "Minimum ADX")
        self.spike_multiplier = self.input.float(2.0, "Max Candle Spike Multiplier",
                                                 tooltip="If the candle is this many times larger than the average candle, block the trade.")

    def on_bar(self):
        atr = ta.atr(self.ut_atr_period)
        n_loss = self.ut_key * atr
        prev_stop = nz(self.H("x_stop")[1], 0.0)
        if self.close > prev_stop and self.close[1] > prev_stop:
            x_stop = pmath.max(prev_stop, self.close - n_loss)
        elif self.close < prev_stop and self.close[1] < prev_stop:
            x_stop = pmath.min(prev_stop, self.close + n_loss)
        elif self.close > prev_stop:
            x_stop = self.close - n_loss
        else:
            x_stop = self.close + n_loss
        self.H("x_stop").set(x_stop)
        buy_signal = ta.crossover(self.close, x_stop)
        sell_signal = ta.crossunder(self.close, x_stop)
        rsi_value = ta.rsi(self.close, self.rsi_period)
        di_plus, di_minus, adx_value = ta.dmi(self.adx_period, self.adx_period)
        current_candle_size = self.high - self.low
        average_candle_size = ta.atr(14)
        is_not_a_spike = current_candle_size <= (average_candle_size * self.spike_multiplier)
        in_trade_window = not na(self.time_fn(None, "0915-1500:1234567", "Asia/Kolkata"))
        enter_pe_sell = (buy_signal and (rsi_value >= self.rsi_pe_min and rsi_value <= self.rsi_pe_max)
                         and adx_value > self.adx_threshold and is_not_a_spike)
        enter_ce_sell = (sell_signal and (rsi_value >= self.rsi_ce_min and rsi_value <= self.rsi_ce_max)
                         and adx_value > self.adx_threshold and is_not_a_spike)
        st = self.strategy
        if in_trade_window:
            if enter_pe_sell:
                st.entry("PE_Sell_Sim", st.long)
            if enter_ce_sell:
                st.entry("CE_Sell_Sim", st.short)
        if not in_trade_window:
            st.close_all(comment="3 PM Exit")
        self.plot(x_stop, color=color.green if self.close > x_stop else color.red, title="UT Bot Stop", linewidth=2)
